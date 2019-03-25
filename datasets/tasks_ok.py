# celery reconciliation tasks align_tgn(), align_whg() and related functions
from __future__ import absolute_import, unicode_literals
from celery.decorators import task
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.gis.geos import Polygon, Point, LineString
import logging
##
import sys, os, re, json, codecs, datetime, time, csv, random
from copy import deepcopy
from pprint import pprint
from areas.models import Area
from datasets.es_utils import makeDoc, esInit
from datasets.models import Dataset, Hit
from datasets.regions import regions as region_hash
from datasets.utils import roundy, fixName, classy, bestParent, elapsed, hully, HitRecord
from places.models import Place
##
import shapely.geometry as sgeo
from geopy import distance
from elasticsearch import Elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
##

def types(hit):
  type_array = []
  for t in hit["_source"]['types']:
    if bool(t['placetype'] != None):
      type_array.append(t['placetype']+', '+str(t['display']))
  return type_array

def names(hit):
  name_array = []
  for t in hit["_source"]['names']:
    if bool(t['name'] != None):
      name_array.append(t['name']+', '+str(t['display']))
  return name_array

def hitRecord(hit,search_loc=None):
  hit = hit
  #print(search_loc,hit)
  type_array = types(hit)
  name_array = names(hit)
  es_loc = hit['_source']['location']
  if search_loc != None and es_loc['coordinates'][0] != None:
    # get distance between search_loc and es_loc()
    # if MultiPoint get centroid
    s = reverse(shapely.geometry.MultiPoint(search_loc['coordinates']).centroid.coords[0]) \
          if len(search_loc['coordinates']) > 1 \
            else reverse(shapely.geometry.Point(search_loc['coordinates'][0]).coords[0])
    t = tuple([es_loc['coordinates'][1],es_loc['coordinates'][0]])
    dist = int(distance.distance(s,t).km)
    #print(dist)
  else:
    dist = '?'
  hitrec = str(dist) +'km\t'+ "%(tgnid)s\t%(title)s\t%(parents)s\t" % hit['_source'] + \
      str(type_array) + '\t'
  #hitrec += "%(lat)s\t%(lon)s\t%(note)s" % hit['_source'] + '\t'
  hitrec += "%(location)s\t%(note)s" % hit['_source'] + '\t'
  hitrec += str(name_array) + '\n'
  return hitrec

def toGeoJSON(hit):
  src = hit['_source']
  feat = {"type": "Feature", "geometry": src['location'],
            "aatid": hit['_id'], "tgnid": src['tgnid'],
            "properties": {"title": src['title'], "parents": src['parents'], "names": names(hit), "types": types(hit) } }
  return feat

def reverse(coords):
  fubar = [coords[1],coords[0]]
  return fubar


# user-supplied spatial bounds
def get_bounds_filter(bounds,idx):
  #print('bounds',bounds)
  id = bounds['id'][0]
  areatype = bounds['type'][0]
  area = Area.objects.get(id = id)
  # TODO: area always a hull polygon now; test MultiPolygon
  geofield = "geoms.location" if idx == 'whg' else "location"
  filter = { "geo_shape": {
    geofield: {
        "shape": {
          "type": "polygon" if areatype == 'userarea' else "multipolygon",
          "coordinates": area.geojson['coordinates']
        },
        "relation": "intersects" if idx=='whg' else 'within' # within | intersects | contains
      }
  }} 
  return filter

#
def es_lookup_tgn(qobj, *args, **kwargs):
  #print('qobj',qobj)
  bounds = kwargs['bounds']
  hit_count = 0

  # empty result object
  result_obj = {
      'place_id': qobj['place_id'], 'hits':[],
        'missed':-1, 'total_hits':-1
    }  

  # array (includes title)
  variants = list(set(qobj['variants']))

  # bestParent() coalesces mod. country and region; countries.json
  parent = bestParent(qobj)

  # pre-computed in sql
  # minmax = row['minmax']

  # getty aat numerical identifiers
  placetypes = list(set(qobj['placetypes']))

  # base query: name, type, parent, bounds if specified
  # geo_polygon filter added later for pass1; used as-is for pass2
  qbase = {"query": { 
    "bool": {
      "must": [
        {"terms": {"names.name":variants}},
        {"terms": {"types.id":placetypes}}
        ],
      "should":[
        {"terms": {"parents":parent}}
        #,{"terms": {"types.id":placetypes}}
        ],
      "filter": [get_bounds_filter(bounds,'tgn')] if bounds['id'] != ['0'] else []
    }
  }}

  qbare = {"query": { 
    "bool": {
      "must": [
        {"terms": {"names.name":variants}}
        ],
      "should":[
        {"terms": {"parents":parent}}                
        ],
      "filter": [get_bounds_filter(bounds,'tgn')] if bounds['id'] != ['0'] else []
    }
  }}

  # grab deep copy of qbase, add w/geo filter if 'geom'
  q1 = deepcopy(qbase)

  # create 'within polygon' filter and add to q1
  if 'geom' in qobj.keys():
    location = qobj['geom']
    # always polygon returned from hully(g_list)
    filter_within = { "geo_shape": {
      "location": {
        "shape": {
          "type": location['type'],
          "coordinates" : location['coordinates']
        },
        "relation": "within" # within | intersects | contains
      }
    }}    
    q1['query']['bool']['filter'].append(filter_within)
    #filter_within = { "geo_polygon" : {
      #"location.coordinates" : {
          ## ignore outer brackets; dunno why
          #"points" : location['coordinates'][0] if location['type'] == "Polygon" \
          #else location['coordinates'][0][0]
        #}
      #}}

  # /\/\/\/\/\/
  # pass1: must[name]; should[type,parent]; filter[bounds,geom]
  # /\/\/\/\/\/
  print('q1',q1)
  try:
    res1 = es.search(index="tgn_shape", body = q1)
    hits1 = res1['hits']['hits']
  except:
    print('pass1 error:',sys.exc_info())
  if len(hits1) > 0:
    for hit in hits1:
      hit_count +=1
      hit['pass'] = 'pass1'
      result_obj['hits'].append(hit)
  elif len(hits1) == 0:
    # /\/\/\/\/\/
    # pass2: revert to qbase{} (drops geom)
    # /\/\/\/\/\/  
    q2 = qbase
    print('q2 (base)',q2)
    try:
      res2 = es.search(index="tgn_shape", body = q2)
      hits2 = res2['hits']['hits']
    except:
      print('pass2 error:',sys.exc_info()) 
    if len(hits2) > 0:
      for hit in hits2:
        hit_count +=1
        hit['pass'] = 'pass2'
        result_obj['hits'].append(hit)
    elif len(hits2) == 0:
      # /\/\/\/\/\/
      # pass3: revert to qbare{} (drops placetype)
      # /\/\/\/\/\/  
      q3 = qbare
      print('q3 (bare)',q3)
      try:
        res3 = es.search(index="tgn_shape", body = q3)
        hits3 = res3['hits']['hits']
      except:
        print('pass3 error:',sys.exc_info())        
      if len(hits3) > 0:
        for hit in hits3:
          hit_count +=1
          hit['pass'] = 'pass3'
          result_obj['hits'].append(hit)
      else:
        # no hit at all, name & bounds only
        result_obj['missed'] = qobj['place_id']
  result_obj['hit_count'] = hit_count
  return result_obj

@task(name="align_tgn")
def align_tgn(pk, *args, **kwargs):
  ds = get_object_or_404(Dataset, id=pk)
  bounds = kwargs['bounds']
  #bounds = {'type': ['userarea'], 'id': ['65']} # Alcedo 
  #bounds = {'type': ['region'], 'id': ['76']}  # C. America
  print('bounds:',bounds,type(bounds))
  hit_parade = {"summary": {}, "hits": []}
  [nohits,tgn_es_errors,features] = [[],[],[]]
  [count, count_hit, count_nohit, total_hits, count_p1, count_p2, count_p3] = [0,0,0,0,0,0,0]
  start = datetime.datetime.now()

  # build query object
  #for place in ds.places.all()[:50]:
  for place in ds.places.all():
    #place=get_object_or_404(Place,id=131735) # Caledonian Canal (ne)
    #place=get_object_or_404(Place,id=131648) # Atengo river (ne)
    #place=get_object_or_404(Place,id=81655) # Atlas Mountains
    #place=get_object_or_404(Place,id=124653) # !Kung (dplace)
    #place=get_object_or_404(Place,id=124925) # Abenaki (dplace)
    #place=get_object_or_404(Place, id=125681) # Chukchi (dplace)
    count +=1
    qobj = {"place_id":place.id,"src_id":place.src_id,"title":place.title}
    [variants,geoms,types,ccodes,parents]=[[],[],[],[],[]]

    # ccodes (2-letter iso codes)
    for c in place.ccodes:
      ccodes.append(c)
    qobj['countries'] = place.ccodes

    # types (Getty AAT identifiers)
    for t in place.types.all():
      types.append(t.json['identifier'])
    qobj['placetypes'] = types

    # names
    for name in place.names.all():
      variants.append(name.toponym)
    qobj['variants'] = variants

    # parents
    # TODO: other relations
    for rel in place.related.all():
      if rel.json['relation_type'] == 'gvp:broaderPartitive':
        parents.append(rel.json['label'])
    qobj['parents'] = parents

    # align_whg geoms
    if len(place.geoms.all()) > 0:
      g_list =[g.json for g in place.geoms.all()]
      # make everything a simple polygon hull for spatial filter
      qobj['geom'] = hully(g_list)
          
    ## run pass1-pass3 ES queries
    try:
      result_obj = es_lookup_tgn(qobj, bounds=bounds)
    except:
      print('es_lookup_tgn failed:',sys.exc_info())
      
    if result_obj['hit_count'] == 0:
      count_nohit +=1
      nohits.append(result_obj['missed'])
    else:
      count_hit +=1
      total_hits += len(result_obj['hits'])
      print("hit[0]: ",result_obj['hits'][0]['_source'])      
      for hit in result_obj['hits']:
        if hit['pass'] == 'pass1': 
          count_p1+=1 
        elif hit['pass'] == 'pass2': 
          count_p2+=1
        elif hit['pass'] == 'pass3': 
          count_p3+=1
        hit_parade["hits"].append(hit)
        # print('creating hit:',hit)
        loc = hit['_source']['location'] if 'location' in hit['_source'].keys() else None
        new = Hit(
          authority = 'tgn',
          authrecord_id = hit['_id'],
          dataset = ds,
          place_id = get_object_or_404(Place, id=qobj['place_id']),
          task_id = align_tgn.request.id,
          query_pass = hit['pass'],
          # consistent, for review display
          json = normalize(hit['_source'],'tgn'),
          src_id = qobj['src_id'],
          score = hit['_score'],
          geom = loc,
          reviewed = False,
        )
        new.save()
  end = datetime.datetime.now()

  print('tgn ES errors:',tgn_es_errors)
  hit_parade['summary'] = {
      'count':count,
      'got_hits':count_hit,
      'total': total_hits, 
      'pass1': count_p1, 
      'pass2': count_p2, 
      'pass3': count_p3,
      'no_hits': {'count': count_nohit },
      'elapsed': elapsed(end-start)
    }
  print("summary returned",hit_parade['summary'])
  return hit_parade['summary']

def parseWhen(when):
  print('when to parse',when)
  timespan = 'parse me now'
  return timespan
def ccDecode(ccodes):
  print('ccodes to parse',ccodes)
  countries = 'parse me now'
  return countries

# create normalized json field for hits from any authority
def normalize(h,auth):
  if auth == 'whg':
    try:
      rec = HitRecord(h['whg_id'], h['place_id'], h['dataset'], h['src_id'], h['title'])
    
      # add elements if non-empty in index record
      rec.variants = [n['toponym'] for n in h['names']] # always >=1 names
      rec.types = [t['label']+' ('+t['src_label']  +')' if 'src_label' in t.keys() else '' \
                  for t in h['types']] if len(h['types']) > 0 else []
      rec.ccodes = ccDecode(h['ccodes']) if len(h['ccodes']) > 0 else []
      rec.parents = ['partOf: '+r.label+' ('+parseWhen(r['when']['timespans'])+')' for r in h['relations']] \
                  if 'relations' in h.keys() and len(h['relations']) > 0 else []
      rec.descriptions = h['descriptions'] if len(h['descriptions']) > 0 else []
      rec.geoms = [{
        "type":h['geoms'][0]['location']['type'], 
        "coordinates":h['geoms'][0]['location']['coordinates'],
        "id":h['place_id'], \
        "ds":"whg"}] \
        if len(h['geoms'])>0 else []
      #rec.geoms = [g['location'] for g in h['geoms']] \
                  #if len(h['geoms']) > 0 else []
      rec.minmax = dict(sorted(h['minmax'].items(),reverse=True)) if len(h['minmax']) > 0 else []
      #rec.whens = [parseWhen(t) for t in h['timespans']] \
                  #if len(h['timespans']) > 0 else []
      rec.links = [l['type']+': '+l['identifier'] for l in h['links']] \
                  if len(h['links']) > 0 else []
    except:
      print("normalize(whg) error:", h['place_id'], sys.exc_info())    
  
  elif auth == 'tgn':
    # h=hit['_source']; ['tgnid', 'title', 'names', 'suggest', 'types', 'parents', 'note', 'location']
    # whg_id, place_id, dataset, src_id, title
    # h['location'] = {'type': 'point', 'coordinates': [105.041, 26.398]}
    try:
      rec = HitRecord(-1, -1, 'tgn', h['tgnid'], h['title'])
      rec.variants = [n['toponym'] for n in h['names']] # always >=1 names
      rec.types = [t['placetype']+' ('+t['id']  +')' for t in h['types'] ] if len(h['types']) > 0 else []
      rec.ccodes = []
      rec.parents = ' > '.join(h['parents']) if len(h['parents']) > 0 else []
      rec.descriptions = [h['note']] if h['note'] != None else []
      rec.geoms = [{
        "type":h['location']['type'], 
        "coordinates":h['location']['coordinates'],
        "id":h['tgnid'], \
        "ds":"tgn"}] \
        if h['location'] != None else []
      #rec.geoms = [h['location']] if h['location'] != None else []
      rec.minmax = []
      #rec.whens =[]
      rec.links = []
    except:
      print("normalize(tgn) error:", h['tgnid'], sys.exc_info())
  return rec.toJSON()

#
def nextID(es):
  q={"query": {"bool": {"must" : {"match_all" : {}} }},
       "sort": [{"whg_id": {"order": "desc"}}],
       "size": 1  
       }
  try:
    res = es.search(index='whg', body=q)
    #maxy = int(res['hits']['hits'][0]['_id'])
    maxy = int(res['hits']['hits'][0]['_source']['whg_id'])
  except:
    maxy = 12345677
  return maxy+1
#
def es_lookup_whg(qobj, *args, **kwargs):
  next_id=nextID(es)
  #print('next_id',next_id)
  idx='whg_flat'
  #idx='whg'
  bounds = kwargs['bounds']
  ds = kwargs['dataset']
  place = kwargs['place']
  #bounds = {'type': ['region'], 'id': ['87']}
  #bounds = {'type': ['userarea'], 'id': ['0']}
  hit_count, err_count = [0,0]

  # empty result object
  result_obj = {
    'place_id': qobj['place_id'], 'title': qobj['title'], 
      'hits':[], 'missed':-1, 'total_hits':-1
  }  

  # initial for pass1
  qlinks = {"query": { 
     "bool": {
       "must": [
          {"terms": {"links.identifier": qobj['links'] }}
        ],
        "should": [
          {"terms": {"names.toponym": qobj['variants']}}
        ]
     }
  }}
  
  # base query: name, type, bounds if specified
  qbase = {"query": { 
    "bool": {
      "must": [
        #{"terms": {"names.toponym": qobj['variants']}},
        {"match": {"names.toponym": qobj['title']}},
        {"terms": {"types.identifier": qobj['placetypes']}}
        ],
      "filter": [get_bounds_filter(bounds,'whg')] if bounds['id'] != ['0'] else []
    }
  }}
  
  # suggest w/spatial experiment: can't do type AND geom contexts
  qsugg = {
    "suggest": {
      "suggest" : {
        "prefix" : qobj['title'],
        "completion" : {
          "field" : "suggest",
          "size": 10,
          "contexts": 
            {"place_type": qobj['placetypes']}
        }
      }
  }}
  
  # last gasp: only name(s) and bounds
  qbare = {"query": { 
    "bool": {
      "must": [
        {"terms": {"names.toponym":qobj['variants']}}
        ],
      "should":[
        {"terms": {"parents":bestParent(qobj)}}                
        ],
      "filter": [get_bounds_filter(bounds,'whg')] if bounds['id'] != ['0'] else []
    }
  }}

  # if geom, define intersect filter & apply to qbase (q2)
  if 'geom' in qobj.keys():
    # call it location
    location = qobj['geom']
    #print('location for filter_intersects_area:',location)
    filter_intersects_area = { "geo_shape": {
      "geoms.location": {
        "shape": {
          # always a polygon, from hully(g_list)
          "type": location['type'],
            "coordinates" : location['coordinates']
        },
        "relation": "intersects" # within | intersects | contains
      }
    }}
    qbase['query']['bool']['filter'].append(filter_intersects_area)
    
    repr_point=list(Polygon(location['coordinates'][0]).centroid.coords) \
                    if location['type'].lower() == 'polygon' else \
                    list(LineString(location['coordinates']).centroid.coords) \
                    if location['type'].lower() == 'linestring' else \
                    list(Point(location['coordinates']).coords)
    
    qsugg['suggest']['suggest']['completion']['contexts']={"place_type": qobj['placetypes']}, \
      {"representative_point": {"lon":repr_point[0] , "lat":repr_point[1], "precision": "100km"}}
  
  # grab copies
  q1 = qlinks
  q2 = qbase #qsugg
  q3 = qbare
  count_seeds=0
  
  # /\/\/\/\/\/
  # pass1: must[links]; should[names->variants]
  # /\/\/\/\/\/
  try:
    print("q1:", q1)
    res1 = es.search(index=idx, body = q1)
    hits1 = res1['hits']['hits']
  except:
    print("q1, error:", q1, sys.exc_info())
  if len(hits1) > 0:
    for hit in hits1:
      hit_count +=1
      hit['pass'] = 'pass1'
      result_obj['hits'].append(hit)
  elif len(hits1) == 0:
  # if this is black, index place as a parent immediately
    #if ds == 'black':
      #parent_obj = makeDoc(place,'none')
      #parent_obj['relation']={"name":"parent"}
      #parent_obj['whg_id']=maxy+2
      ## add its own names to the suggest field
      #for n in parent_obj['names']:
        #parent_obj['suggest']['input'].append(n['toponym']) 
      # index it
      #try:
        #res = es.index(index=idx, doc_type='place', id=maxy+2, body=json.dumps(parent_obj))
        ##res = es.index(index=idx, doc_type='place', body=json.dumps(parent_obj))
        #count_seeds +=1
      #except:
        #print('failed indexing '+str(place.id), parent_obj)
        #err_black-whg.write(str({"pid":place.id, "title":place.title})+'\n')
  # /\/\/\/\/\/
  # pass2: must[name, type]; should[parent]; filter[geom, bounds]
  # /\/\/\/\/\/
    try:
      print("q2:", q2)
      res2 = es.search(index=idx, body = q2)
      hits2 = res2['hits']['hits']
    except:
      print("q2, error:", q2, sys.exc_info())
    if len(hits2) > 0:
      for hit in hits2:
        hit_count +=1
        hit['pass'] = 'pass2'
        result_obj['hits'].append(hit)
    elif len(hits2) == 0:
      # /\/\/\/\/\/
      # pass3: must[name]; should[parent]; filter[bounds]
      # /\/\/\/\/\/
      try:
        print("q3:", q3)
        res3 = es.search(index=idx, body = q3)
        hits3 = res3['hits']['hits']
      except:
        print("q2, error:", q3, sys.exc_info())
      if len(hits3) > 0:
        for hit in hits3:
          hit_count +=1
          hit['pass'] = 'pass3'
          result_obj['hits'].append(hit)
      else:
        # no hit at all
        result_obj['missed'] = qobj['place_id']
  result_obj['hit_count'] = hit_count
  return result_obj

#
@task(name="align_whg")
def align_whg(pk, *args, **kwargs):
  #print('align_whg kwargs:', str(kwargs))
  #fin = codecs.open(tempfn, 'r', 'utf8')
  ds = get_object_or_404(Dataset, id=pk)
  #if ds.id==1:
    #err_black_whg = codecs.open('err_black-whg.txt', mode='w', encoding='utf8')
    #esInit('whg')
  
  # dummies for testing
  bounds = {'type': ['userarea'], 'id': ['0']}
  #bounds = {'type': ['region'], 'id': ['76']}
  #bounds = kwargs['bounds']

  # TODO: system for region creation
  hit_parade = {"summary": {}, "hits": []}
  nohits = [] # place_id list for 0 hits
  features = []
  errors=[]
  [count, count_hit, count_nohit, total_hits, count_p1, count_p2, count_p3, count_errors] = [0,0,0,0,0,0,0,0]
  #print('align_whg celery task id:', align_whg.request.id)
  start = datetime.datetime.now()

  # build query object, send, save hits
  #for place in ds.places.all()[9:12]:
  for place in ds.places.all():
    #place=ds.places.first()
    #place=get_object_or_404(Place,id=81741) # Baalbek (lb)
    #place=get_object_or_404(Place,id=84778) # Baalbek/Heliopolis (lb)
    #place=get_object_or_404(Place,id=84777) # Heliopolis (eg)
    count +=1
    #whg_id +=1
    qobj = {"place_id":place.id, "src_id":place.src_id, "title":place.title}
    links=[]; ccodes=[]; types=[]; variants=[]; parents=[]; geoms=[]; 

    ## links
    for l in place.links.all():
      links.append(l.json['identifier'])
    qobj['links'] = links

    ## ccodes (2-letter iso codes)
    for c in place.ccodes:
      ccodes.append(c)
    qobj['countries'] = list(set(place.ccodes))

    ## types (Getty AAT identifiers)
    ## account for 'null' in 97 black records
    for t in place.types.all():
      if t.json['identifier'] != None:
        types.append(t.json['identifier'])
      else:
        # inhabited place, cultural group, site
        types.extend(['aat:300008347','aat:300387171','aat:300000809'])
    qobj['placetypes'] = types

    ## names
    for name in place.names.all():
      variants.append(name.toponym)
    qobj['variants'] = variants

    ## parents
    for rel in place.related.all():
      if rel.json['relation_type'] == 'gvp:broaderPartitive':
        parents.append(rel.json['label'])
    qobj['parents'] = parents

    ## geoms
    if len(place.geoms.all()) > 0:
      # any geoms at all...
      g_list =[g.json for g in place.geoms.all()]
      # make everything a simple polygon hull for spatial filter purposes
      qobj['geom'] = hully(g_list)

    #print('qobj in align_whg():', qobj)

    ## run pass1-pass3 ES queries
    result_obj = es_lookup_whg(qobj, bounds=bounds, dataset=ds.label, place=place)

    if result_obj['hit_count'] == 0:
      count_nohit +=1
      # for black, create parent record immediately
      if ds.label == 'black':
        print('created parent:',result_obj['place_id'],result_obj['title'])
      nohits.append(result_obj['missed'])
    else:
      count_hit +=1
      count_errors = 0
      total_hits += result_obj['hit_count']
      print("hit['_source']: ",result_obj['hits'][0]['_source'])
      for hit in result_obj['hits']:
        if hit['pass'] == 'pass1':
          count_p1+=1 
        elif hit['pass'] == 'pass2': 
          count_p2+=1
        elif hit['pass'] == 'pass3': 
          count_p3+=1
        hit_parade["hits"].append(hit)
        loc = hit['_source']['geoms'] if 'geoms' in hit['_source'].keys() else None
        try:
          new = Hit(
            authority = 'whg',
            authrecord_id = hit['_id'],
            dataset = ds,
            place_id = get_object_or_404(Place, id=qobj['place_id']),
            task_id = align_whg.request.id,
            #task_id = 'abcxxyyzz',
            query_pass = hit['pass'],
            # consistent json for review display
            json = normalize(hit['_source'],'whg'),
            src_id = qobj['src_id'],
            score = hit['_score'],
            geom = loc,
            reviewed = False,
          )
          new.save()
        except:
          count_errors +=1
          #pass
          print("hit _source, error:", hit, sys.exc_info())
  end = datetime.datetime.now()
  # ds.status = 'recon_whg'
  #print('features:',features)
  hit_parade['summary'] = {
    'count':count,
    'got_hits':count_hit,
    'total': total_hits, 
    'pass1': count_p1, 
    'pass2': count_p2, 
    'pass3': count_p3,
    'no_hits': {'count': count_nohit },
    'elapsed': elapsed(end-start)
    #'skipped': count_errors
  }
  #if err_black_whg != None: err_black_whg.close()
  print("hit_parade['summary']",hit_parade['summary'])
  return hit_parade['summary']

def read_delimited(infile, username):
  # some WKT is big
  csv.field_size_limit(100000000)
  result = {'format':'delimited','errors':{}}
  # required fields
  # TODO: req. fields not null or blank
  # required = ['id', 'title', 'name_src', 'ccodes', 'lon', 'lat']
  required = ['id', 'title', 'name_src']

  # learn delimiter [',',';']
  # TODO: falling back to tab if it fails; need more stable approach
  try:
    dialect = csv.Sniffer().sniff(infile.read(16000),['\t',';','|'])
    result['delimiter'] = 'tab' if dialect.delimiter == '\t' else dialect.delimiter
  except:
    dialect = '\t'
    result['delimiter'] = 'tab'

  reader = csv.reader(infile, dialect)
  result['count'] = sum(1 for row in reader)

  # get & test header (not field contents yet)
  infile.seek(0)
  header = next(reader, None) #.split(dialect.delimiter)
  result['columns'] = header

  # TODO: specify which is missing
  if not len(set(header) & set(required)) == 3:
    result['errors']['req'] = 'missing a required column (id,name,name_src)'
    return result
  if ('min' in header and 'max' not in header) \
       or ('max' in header and 'min' not in header):
    result['errors']['req'] = 'if a min, must be a max - and vice versa'
    return result
  if ('lon' in header and 'lat' not in header) \
       or ('lat' in header and 'lon' not in header):
    result['errors']['req'] = 'if a lon, must be a lat - and vice versa'
    return result

  #print(header)
  rowcount = 1
  geometries = []
  for r in reader:
    rowcount += 1

    # length errors
    if len(r) != len(header):
      if 'rowlength' in result['errors'].keys():
        result['errors']['rowlength'].append(rowcount)
      else:
        result['errors']['rowlength'] = [rowcount]


    # TODO: write geojson? make map? so many questions
    if 'lon' in header:
      print('type(lon): ', type('lon'))
      if (r[header.index('lon')] not in ('',None)) and \
               (r[header.index('lat')] not in ('',None)):
        feature = {
                  'type':'Feature',
                    'geometry': {'type':'Point',
                                 'coordinates':[ float(r[header.index('lon')]), float(r[header.index('lat')]) ]},
                    'properties': {'id':r[header.index('id')], 'name': r[header.index('title')]}
                }
        # TODO: add properties to geojson feature?
        # props = set(header) - set(required)
        # print('props',props)
        # for p in props:
        #     feature['properties'][p] = r[header.index(p)]
        geometries.append(feature)

  if len(result['errors'].keys()) == 0:
    # don't add geometries to result
    # TODO: write them to a user GeoJSON file?
    # print('got username?', username)
    # print('2 geoms:', geometries[:2])
    # result['geom'] = {"type":"FeatureCollection", "features":geometries}
    print('looks ok')
  else:
    print('got errors')
  return result

def read_lpf(infile):
  return 'reached tasks.read_lpf()'

# ES geoms filter
#"filter": {
  #"geo_shape": {
      #"location": {
          #"shape": {
              #"type": "envelope",
                #"coordinates" : [[13.0, 53.0], [14.0, 52.0]]
                #},
            #"relation": "within" # within | intersects | contains
        #}
    #}
#}
# ES geo_bounding_box filter
# {
#   "top_left" : {"lat" : 40.73, "lon" : -74.1},
#   "bottom_right" : {"lat" : 40.01,"lon" : -71.12}
# }

# ES geo_polygon filter
# {
#   "points" : [ [-70, 40], [-80, 30], [-90, 20] ]
# }

# "geo_shape": { "location.coordinates": {"shape":
#         {
#             "type": "envelope",
#             "coordinates" : [[13.0, 53.0], [14.0, 52.0]]
#         },
#         "relation": "within"
#     }
# }

# POINTS ARE GETTING BUFFERED EARLIER
#def makeBuffer(point,val):
  #from shapely import geometry as sgeo
  #from geomet import wkt
  #buffer = sgeo.Point(point[0],point[1]).buffer(val).to_wkt()
  #return wkt.loads(buffer)['coordinates']

#filter_intersects_point = { "geo_shape": {
  #"geoms.location": {
      #"shape": {
        #"type": "polygon",
          #"coordinates" : makeBuffer(location['coordinates'], 2.0)
      #},
      #"relation": "intersects" # within | intersects | contains
    #}
#}} if location['type'] == "Point" else {}

# selectively add filters to queries
#if location['type'] == 'Point':
  #q1['query']['bool']['filter'].append(filter_intersects_point)
#elif location['type'] in ('Polygon','MultiPolygon'): # hull
