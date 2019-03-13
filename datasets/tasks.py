# functions related to datasets app
from __future__ import absolute_import, unicode_literals
from celery.decorators import task
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.gis.geos import Polygon, Point

import sys, os, re, json, codecs, datetime, time, csv
import random
from pprint import pprint
from datasets.models import Dataset, Hit
from places.models import Place
from areas.models import Area
from datasets.regions import regions as region_hash
##
import shapely.geometry as sgeo
from geopy import distance
from datasets.utils import roundy, fixName, classy, bestParent, elapsed, hully, HitRecord
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


# used for align_tgn 
# TODO: implement 'geo_shape' for tgn index
def get_bbox_filter(bounds):
  print('bounds',bounds)
  id = bounds['id'][0]
  type = bounds['type'][0]
  if type == 'region':
    filter = {
      "geo_bounding_box" : {"location.coordinates" : region_hash[id]}
    }
  elif type == 'userarea':
    area = Area.objects.get(id = id)
    filter = {
      "geo_polygon": {
          "location.coordinates" : {"points": area.geojson['coordinates'][0]}
        }
    }
    return filter

# user-supplied spatial bounds
def get_bounds_filter(bounds,idx):
  #print('bounds',bounds)
  id = bounds['id'][0]
  type = bounds['type'][0]
  area = Area.objects.get(id = id)
  # TODO: area always a hull polygon now; test MultiPolygon
  geofield = "geoms.location" if idx == 'whg' else "location"
  filter = { "geo_shape": {
    geofield: {
        "shape": {
          "type": "polygon",
            "coordinates": area.geojson['coordinates']
            #"coordinates" : location['coordinates'] if location['type'] == "Polygon" \
            #else location['coordinates'][0][0]
        },
        "relation": "intersects" #if idx=='whg' else 'within' # within | intersects | contains
      }
  }} 
  return filter

#
def es_lookup(qobj, *args, **kwargs):
  # print('qobj',qobj)
  bounds = kwargs['bounds']
  print('bounds:',bounds)
  hit_count = 0
  #search_name = fixName(qobj['prefname'])

  # empty result object
  result_obj = {
      'place_id': qobj['place_id'], 'hits':[],
        'missed':-1, 'total_hits':-1
    }  

  # array (includes title)
  variants = qobj['variants']

  # bestParent() coalesces mod. country and region; countries.json
  parent = bestParent(qobj)

  # pre-computed in sql
  # minmax = row['minmax']

  # getty aat numerical identifiers
  placetypes = qobj['placetypes']

  # base query: name, type, parent, bounds if specified
  qbase = {"query": { 
    "bool": {
      "must": [
        {"terms": {"names.name":variants}},
        {"terms": {"types.id":placetypes}}
        ],
      "should":[
        {"terms": {"parents":parent}}                
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


  # grab copy of qbase
  q1 = qbase

  # if geometry is supplied, define spatial filters & apply one to copy of qbase
  if 'geom' in qobj.keys():
    # call it location
    location = qobj['geom']

    filter_within = { "geo_polygon" : {
          "location.coordinates" : {
              # extra bracket pair(s), dunno why
                "points" : location['coordinates'][0] if location['type'] == "Polygon" \
                else location['coordinates'][0][0]
            }
        }}

    filter_dist_100 = {"geo_distance" : {
          "ignore_unmapped": "true",
            "distance" : "100km",
            "location.coordinates" : qobj['geom']['coordinates']
        }}

    filter_dist_200 = {"geo_distance" : {
          "ignore_unmapped": "true",
            "distance" : "200km",
            "location.coordinates" : qobj['geom']['coordinates']
        }}

    # selectively add filters to queries
    if location['type'] == 'Point':
      q1['query']['bool']['filter'].append(filter_dist_200)
    elif location['type'] in ('Polygon','MultiPolygon'): # hull
      q1['query']['bool']['filter'].append(filter_within)


  # pass1: name, type, parent, study_area, geom if provided
  print('q1',q1)
  res1 = es.search(index="tgn201902", body = q1)
  hits1 = res1['hits']['hits']
  # 1 or more hits
  if len(hits1) > 0:
    for hit in hits1:
      hit_count +=1
      hit['pass'] = 'pass1'
      result_obj['hits'].append(hit)
  elif len(hits1) == 0:
  # pass2: drop geom (revert to qbase{})
    q2 = qbase
    print('q2 (base)',q2)
    res2 = es.search(index="tgn201902", body = q2)
    hits2 = res2['hits']['hits']
    if len(hits2) > 0:
      for hit in hits2:
        hit_count +=1
        hit['pass'] = 'pass2'
        result_obj['hits'].append(hit)
    elif len(hits2) == 0:
      # drop type, parent using qbare{}
      q3 = qbare
      print('q3 (bare)',q3)
      res3 = es.search(index="tgn201902", body = q3)
      hits3 = res3['hits']['hits']
      if len(hits3) > 0:
        for hit in hits3:
          hit_count +=1
          hit['pass'] = 'pass3'
          result_obj['hits'].append(hit)
      else:
        # no hit at all, name & bounds only
        result_obj['missed'] = qobj['place_id']
        # TODO: q4 for fuzzy names?
  result_obj['hit_count'] = hit_count
  return result_obj

@task(name="align_tgn")
def align_tgn(pk, *args, **kwargs):
  ds = get_object_or_404(Dataset, id=pk)
  bounds = kwargs['bounds']
  print('bounds:',bounds,type(bounds))
  # TODO: system for region creation
  hit_parade = {"summary": {}, "hits": []}
  nohits = [] # place_id list for 0 hits
  features = []
  [count, count_hit, count_nohit, total_hits, count_p1, count_p2, count_p3] = [0,0,0,0,0,0,0]
  # print('celery task id:', align_tgn.request.id)
  start = datetime.datetime.now()

  # build query object, send, save hits
  # for place in ds.places.all()[:50]:
  for place in ds.places.all():
    count +=1
    query_obj = {"place_id":place.id,"src_id":place.src_id,"prefname":place.title}
    variants=[]; geoms=[]; types=[]; ccodes=[]; parents=[]

    # ccodes (2-letter iso codes)
    for c in place.ccodes:
      ccodes.append(c)
    query_obj['countries'] = place.ccodes

    # types (Getty AAT identifiers)
    for t in place.types.all():
      #print('type',t)
      types.append(int(t.json['identifier'][4:]))
    query_obj['placetypes'] = types

    # names
    for name in place.names.all():
      variants.append(name.toponym)
    query_obj['variants'] = variants

    # parents
    for rel in place.related.all():
      if rel.json['relation_type'] == 'gvp:broaderPartitive':
        parents.append(rel.json['label'])
    query_obj['parents'] = parents

    # geoms
    # ignore non-point geometry
    if len(place.geoms.all()) > 0:
      geom = place.geoms.all()[0].json
      if geom['type'] in ('Point','MultiPolygon'):
        query_obj['geom'] = place.geoms.first().json
      elif geom['type'] == 'MultiLineString':
        query_obj['geom'] = hully(geom)

    #print('query_obj:', query_obj)

    # run ES query on query_obj, with bounds
    # regions.regions
    result_obj = es_lookup(query_obj, bounds=bounds)

    if result_obj['hit_count'] == 0:
      count_nohit +=1
      nohits.append(result_obj['missed'])
    else:
      count_hit +=1
      total_hits += result_obj['hit_count']
      # TODO: differentiate hits from passes
      print("hit['_source']: ",result_obj['hits'][0]['_source'])      
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
                    place_id = get_object_or_404(Place, id=query_obj['place_id']),
                    task_id = align_tgn.request.id,
                    # TODO: articulate hit here?
                    query_pass = hit['pass'],
                    json = hit['_source'],
                    src_id = query_obj['src_id'],
                    score = hit['_score'],
                    geom = loc,
                    reviewed = False,
                )
        new.save()
  end = datetime.datetime.now()
  # ds.status = 'recon_tgn'
  # TODO: return summary
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
    }
  print("hit_parade['summary']",hit_parade['summary'])
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
    rec = HitRecord(h['whg_id'], h['place_id'], h['dataset'], h['src_id'], h['title'])
  
    # add elements if non-empty in index record
    rec.variants = [n['toponym'] for n in h['names']] # always >=1 names
    rec.types = [t['label']+' ('+t['src_label']  +')' if 'src_label' in t.keys() else '' \
                for t in h['types']] if len(h['types']) > 0 else []
    rec.ccodes = ccDecode(h['ccodes']) if len(h['ccodes']) > 0 else []
    rec.parents = ['partOf: '+r.label+' ('+parseWhen(r['when']['timespans'])+')' for r in h['relations']] \
                if 'relations' in h.keys() and len(h['relations']) > 0 else []
    rec.descriptions = h['descriptions'] if len(h['descriptions']) > 0 else []
    rec.geoms = [g['location'] for g in h['geoms']] \
                if len(h['geoms']) > 0 else []
    rec.minmax = dict(sorted(h['minmax'].items(),reverse=True)) if len(h['minmax']) > 0 else []
    #rec.minmax = {'start: '+str(h['minmax']['start']), 'end: '+str(h['minmax']['end'])] if len(h['minmax']) > 0 else []
    #[parseWhen(t) for t in h['timespans']] \
                #if len(h['timespans']) > 0 else []
    rec.links = [l['type']+': '+l['identifier'] for l in h['links']] \
                if len(h['links']) > 0 else []
  
    return rec.toJSON()
  
#
def es_lookup_whg(qobj, *args, **kwargs):
  # print('qobj',qobj)
  bounds = kwargs['bounds']
  #bounds = {'type': ['region'], 'id': ['eh']}
  #bounds = {'type': ['userarea'], 'id': ['0']}
  hit_count, err_count = [0,0]
  #search_name = fixName(qobj['prefname'])

  # empty result object
  result_obj = {
      'place_id': qobj['place_id'], 'hits':[],
        'missed':-1, 'total_hits':-1
    }  

  # initial for pass1
  # TODO: automatically accept?
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
        {"match": {"names.toponym": qobj['prefname']}},
        {"terms": {"types.identifier": qobj['placetypes']}}
        ],
      "filter": [get_bounds_filter(bounds,'whg')] if bounds['id'] != ['0'] else []
    }
  }}
  
  # suggester experiment: can't do AND for type and geom
  qsugg = {
    "suggest": {
      "suggest" : {
        "prefix" : qobj['prefname'],
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

  # if geometry is supplied, define spatial intersect filter & apply to q2
  if 'geom' in qobj.keys():
    # call it location
    location = qobj['geom']
    filter_intersects_area = { "geo_shape": {
      "geoms.location": {
          "shape": {
            # always a polygon, from hully(g_list)
            "type": location['type'],
              "coordinates" : location['coordinates']
          },
          "relation": "intersects" # within | intersects | contains
        }
    }} if location['type'] != "Point" else {}
    repr_point=json.loads(Polygon(qobj['geom']['coordinates'][0]).centroid.geojson)['coordinates']
    filter_geo_context = {"representative_point": {"lon":repr_point[0] , "lat":repr_point[1], "precision": "100km"}}
    
    qbase['query']['bool']['filter'].append(filter_intersects_area)
    qsugg['suggest']['suggest']['completion']['contexts']={"place_type": qobj['placetypes']}, \
      {"representative_point": {"lon":repr_point[0] , "lat":repr_point[1], "precision": "100km"}}
  
  # grab copies
  q1 = qlinks
  q2 = qbase
  #q2 = qsugg
  q3 = qbare

  # /\/\/\/\/\/
  # pass1: name, type, parent, study_area, geom if provided
  try:
    res1 = es.search(index="whg_flat", body = q1)
    hits1 = res1['hits']['hits']
  except:
    print("q1, error:", q1, sys.exc_info())
    #sys.exit(1)
  # 1 or more hits
  if len(hits1) > 0:
    for hit in hits1:
      hit_count +=1
      hit['pass'] = 'pass1'
      result_obj['hits'].append(hit)
  elif len(hits1) == 0:
  # /\/\/\/\/\/
  # pass2 must:name, type; should:parent; filter:geom, bounds
    try:
      res2 = es.search(index="whg_flat", body = q2)
      hits2 = res2['hits']['hits']
      #hits2 = res2['suggest']['suggest'][0]['options']
    except:
      print("q2, error:", q2, sys.exc_info())
    if len(hits2) > 0:
      for hit in hits2:
        hit_count +=1
        hit['pass'] = 'pass2'
        result_obj['hits'].append(hit)
    elif len(hits2) == 0:
      # /\/\/\/\/\/
      # pass3 must:name; should:parent; filter:bounds
      try:
        res3 = es.search(index="whg_flat", body = q3)
        hits3 = res3['hits']['hits']
      except:
        print("q2, error:", q3, sys.exc_info())
        #sys.exit(1)
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

#
@task(name="align_whg")
def align_whg(pk, *args, **kwargs):
  #print('align_whg kwargs:', str(kwargs))

  ds = get_object_or_404(Dataset, id=pk)

  bounds = kwargs['bounds']
  # dummies for testing
  #bounds = {'type': ['userarea'], 'id': ['0']}
  #bounds = {'type': ['region'], 'id': ['eh']}

  # TODO: system for region creation
  hit_parade = {"summary": {}, "hits": []}
  nohits = [] # place_id list for 0 hits
  features = []
  [count, count_hit, count_nohit, total_hits, count_p1, count_p2, count_p3] = [0,0,0,0,0,0,0]
  #print('align_whg celery task id:', align_whg.request.id)
  start = datetime.datetime.now()

  # build query object, send, save hits
  #for place in ds.places.all()[:100]:
  for place in ds.places.all():
    #place=ds.places.first()
    #place=get_object_or_404(Place,id=81655) # Atlas Mountains
    #place=get_object_or_404(Place,id=124653) # !Kung
    #place=get_object_or_404(Place,id=127161) # Tanganyika
    count +=1
    query_obj = {"place_id":place.id, "src_id":place.src_id, "prefname":place.title}
    links=[]; ccodes=[]; types=[]; variants=[]; parents=[]; geoms=[]; 

    ## links
    for l in place.links.all():
      links.append(l.json['identifier'])
    query_obj['links'] = links

    ## ccodes (2-letter iso codes)
    for c in place.ccodes:
      ccodes.append(c)
    query_obj['countries'] = place.ccodes

    ## types (Getty AAT identifiers)
    for t in place.types.all():
      types.append(t.json['identifier'])
    query_obj['placetypes'] = types

    ## names
    for name in place.names.all():
      variants.append(name.toponym)
    query_obj['variants'] = variants

    ## parents
    for rel in place.related.all():
      if rel.json['relation_type'] == 'gvp:broaderPartitive':
        parents.append(rel.json['label'])
    query_obj['parents'] = parents

    ## geoms
    if len(place.geoms.all()) > 0:
      # any geoms at all...
      g_list =[g.json for g in place.geoms.all()]
      # make everything a simple polygon hull for spatial filter purposes
      query_obj['geom'] = hully(g_list)
      #if len(g_list) == 1 and g_list[0]['type'] == 'MultiPolygon':
        ## single multipolygon -> use as is...eh not so fast
        #query_obj['geom']=g_list[0]
      #else:
        ## 1 or more points or multilinestrings -> make polygon hull
        #query_obj['geom'] = hully(g_list)

    #print('query_obj:', query_obj)

    ## run pass1-pass3 ES queries
    result_obj = es_lookup_whg(query_obj, bounds=bounds)

    if result_obj['hit_count'] == 0:
      count_nohit +=1
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
        # print('creating hit:',hit)
        loc = hit['_source']['geoms'] if 'geoms' in hit['_source'].keys() else None
        try:
          new = Hit(
            authority = 'whg',
            authrecord_id = hit['_id'],
            dataset = ds,
            place_id = get_object_or_404(Place, id=query_obj['place_id']),
            task_id = align_whg.request.id,
            #task_id = 'abcxxyyzz',
            # TODO: articulate hit here ?
            query_pass = hit['pass'],
            json = normalize(hit['_source'],'whg'),
            src_id = query_obj['src_id'],
            score = hit['_score'],
            geom = loc,
            reviewed = False,
          )
          new.save()
        except:
          count_errors +=1
          pass
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
    'elapsed': elapsed(end-start),
    'skipped': count_errors
  }
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
