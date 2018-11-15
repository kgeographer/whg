# functions related to datasets app
from __future__ import absolute_import, unicode_literals
from celery.decorators import task
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect

import sys, os, re, json, codecs, datetime, time, csv
import random
from pprint import pprint
from .models import Dataset, Hit

##
import shapely.geometry
from geopy import distance
from .recon_utils import roundy, fixName, classy, bestParent
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

def es_lookup(qobj):
    print('qobj',qobj)
    count_single,count_multi,count_nameonly,count_misses = [0,0,0,0]

    search_name = fixName(qobj['prefname'])

    # array (includes title)
    altnames = qobj['altnames']

    # bestParent() coalesces mod. country and region; countries.json
    parent = bestParent(qobj)

    # province if there
    # province = qobj['province']

    # pre-computed in sql
    # minmax = row['minmax']

    # classy() maps Black place types to TGN place types
    # placetypes = classy('tgn',qobj['placetypes'])
    placetypes = qobj['placetypes']

    # geom and centroid are avalable
    location = qobj['geom']

    # TODO: ensure name search on ANY(names.name)
    # TODO: handle variants
    # pass1: name, type, parent
    q1 = {
        "query": {
          "bool": {
              "must": [
                #{"multi_match": {
                    #"query": search_name,
                    #"fields": ["title", "names.name"]}
                #}
                {"terms" : { "names.name" : altnames }}
                # is name in parsed TGN parent string?
                ,{"match": {"parents": parent}}
                # TODO: ensure contributed types are AAT labels
                ,{"match": {"types.placetype": placetypes[0]}}
              ]
              ,"filter" : {
                "geo_distance" : {
                    "ignore_unmapped": "true",
                    "distance" : "50km",
                    "location.coordinates" : qobj['geom']['coordinates']
                }
            }
          }
        }
      }
    # pass2: name, parent
    q2 = {  "query": {
            "bool": {
              "must": [
                #{"multi_match": {
                    #"query": search_name,
                    #"fields": ["title", "names.name"]}
                #},
                {"terms" : { "names.name" : altnames }}
                ,{"match": {"parents": parent}}
              ]
              , "filter" : {
                "geo_distance" : {
                    "ignore_unmapped": "true",
                    "distance" : "50km",
                    "location.coordinates" : qobj['geom']['coordinates']
                }
                }
          }
    }}
    # pass3a: name and distance
    q3 = {  "query": {
            "bool": {
                "must": {
                    #"multi_match": {
                      #"query": search_name,
                      #"fields": ["title", "names.name"]
                  #}
                  "terms" : { "names.name" : altnames }
                }
                ,"filter" : {
                    "geo_distance" : {
                        "ignore_unmapped": "true",
                        "distance" : "200km",
                        # "location.coordinates" : qobj['geom']['coordinates'][0]
                        "location.coordinates" : qobj['geom']['coordinates']
                    }
                }
            }
    }}
    # pass3b: name only
    q4 = { "query": {
        "bool": {
            "must": {
                "terms" : { "names.name" : altnames }
                #"multi_match": {
                  #"query": search_name,
                  #"fields": ["title", "names.name"]
              #}
            }
        }
    }}

    result_obj = {
        'place_id': qobj['place_id'], 'hits':[], 'missed':-1
    }

    # pass1: query [name, type, parent]
    res1 = es.search(index="tgn", body = q1)
    hits1 = res1['hits']['hits']

    # multiple hits
    if len(hits1) > 1:
        count_multi +=1
        result_obj['hits1'].append(hits1)
    # exactly 1 hit
    elif len(hits1) == 1:
        result_obj['hits1'].append(hits1)
        count_single +=1
        type_array = types(hits1[0])
    # no hits on pass1; pass2 with only [name,parent]
    elif len(hits1) == 0:
        res2 = es.search(index="tgn", body = q2)
        hits2 = res2['hits']['hits']
        if len(hits2) > 1:
            result_obj['hits2'].append(hits2)
            count_multi +=1
            #print(row['centroid'],location,str(hits2[0]['_source']['location']))
            # hit_array = []
            # fout_multi.write('\n'+header)
            # for hit in hits2:
            #     fout_multi.write( '\t'+hitRecord(hit,location) )
        # exactly 1 hit
        elif len(hits2) == 1:
            count_single +=1
            # strip out rivers b/c too many false positives when no type is sent
            if any(x['placetype'] == "rivers" for x in hits2[0]['_source']['types']):
                pass
            else:
                result_obj['hits2'].append(hits2)
        # no hits on pass2
        elif len(hits2) == 0:
            # now name only; may yield a few correct matches
            # because place type mapping is imperfect
            # tests geometry (200km)
            if qobj['geom'] != None:
                res3 = es.search(index="tgn", body = q3)
            else:
                res3 = es.search(index="tgn", body = q4) # no geom
            hits3 = res3['hits']['hits']
            if len(hits3) > 0:
                count_nameonly +=1
                result_obj['hits3'].append(hits3)
            else:
                # no hit at all, even on name only
                result_obj['missed'] = qobj['place_id']
                # TODO: make name search fuzzy?

    return result_obj

@task(name="align_tgn")
def align_tgn(pk):
    ds = get_object_or_404(Dataset, id=pk)
    hit_parade = []
    nohits = [] # place_id list for 0 hits
    [count, count_hit, count_nohit] = [0,0,0]
    print('align_tgn():', ds)
    print('celery task id:', align_tgn.request.id)

    # build query object and send
    for place in ds.places.all()[:5]:
        count +=1
        query_obj = {"place_id":place.id,"src_id":place.src_id,"prefname":place.title}
        altnames=[]; geoms=[]; types=[]; ccodes=[]
        for name in place.names.all():
            altnames.append(name.toponym)
        query_obj['altnames'] = altnames
        query_obj['countries'] = place.ccodes
        # TODO: handle multipoint, polygons(?)
        query_obj['geom'] = place.geoms.first().json
        query_obj['placetypes'] = [place.types.first().json['label']]

        # run es query on this record
        result_obj = es_lookup(query_obj)

        if result_obj['missed'] > -1:
            count_nohit +=1
            nohits.append(result_obj['missed'])
        else:
            count_hit +=1
            # TODO: write hit records from pass arrays
            for hit in result_obj['hits1']:
                create_hit(hit)
            # hit_parade[place.id] = result_obj
            # print('result_obj', place.id, result_obj)

    # TODO: write result_obj as hit record
    # task_id, authority, dataset, place_id, authrecord_id, json
    # new = Hit.objects.create(
    #     task_id = align_tgn.request.id,
    #     authority = 'tgn',
    #     dataset = ds.id,
    #     place_id = query_obj['place_id'],
    #     authrecord_id = result_obj['_id'],
    #     json = result_obj,
    # )
    # print('new record: ', new)

    # TODO: return summary
    hit_parade['summary'] = {
        'count':count,
        'got-hits':count_hit,
        'no-hits':{'count':count_nohit,'place_ids':nohits}
    }
    # return hit_parade['summary']
    return hit_parade


def read_delimited(infile, username):
    result = {'format':'delimited','errors':{}}
    # required fields
    # TODO: req. fields not null or blank
    required = ['id', 'name', 'name_src', 'ccodes', 'lon', 'lat']

    # learn delimiter [',',';']
    dialect = csv.Sniffer().sniff(infile.read(16000),['\t',';','|'])
    result['delimiter'] = 'tab' if dialect.delimiter == '\t' else dialect.delimiter

    reader = csv.reader(infile, dialect)
    result['count'] = sum(1 for row in reader)

    # get & test header (not field contents yet)
    infile.seek(0)
    header = next(reader, None) #.split(dialect.delimiter)
    result['columns'] = header

    if not len(set(header) & set(required)) == 6:
        result['errors']['req'] = 'missing required column (id,name,name_src, ccodes,lon,lat)'
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

        # make geojson
        # TODO: test lon, lat makes valid geometry
        if r[header.index('lon')] not in ('', None):
            feature = {
                'type':'Feature',
                'geometry': {'type':'Point',
                             'coordinates':[ float(r[header.index('lon')]), float(r[header.index('lat')]) ]},
                'properties': {'id':r[header.index('id')], 'name': r[header.index('name')]}
            }
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

@task(name="sum_two_numbers")
def add(x, y):
    return x + y

@task(name="multiply_two_numbers")
def mul(x, y):
    total = x * (y * random.randint(3, 100))
    return total

@task(name="sum_list_numbers")
def xsum(numbers):
    return sum(numbers)
