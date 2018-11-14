# functions related to datasets app
from __future__ import absolute_import, unicode_literals
from django.shortcuts import render, get_object_or_404, redirect
from celery.decorators import task

import sys, os, re, json, codecs, datetime, time, csv
import random
from pprint import pprint
from .models import Dataset



@task(name="align_tgn")
def align_tgn(pk):
    ds = get_object_or_404(Dataset, id=pk)
    place_array = []
    print('align_tgn():',ds)
    # build query object on the fly
    for place in ds.places.all()[:10]:
        qobj = {"place_id":place.id,"src_id":place.src_id,"prefname":place.title}
        altnames=[]; geoms=[]; types=[]; ccodes=[]

        for name in place.names.all():
            altnames.append(name.toponym)
        qobj['altnames'] = altnames
        qobj['countries'] = place.ccodes
        # TODO: make multipoint?
        qobj['geoms'] = place.geoms.first().json
        qobj['placetypes'] = [place.types.first().json['label']]
        place_array.append(qobj)
    result = {"places": place_array}
    return result

# {	"placeid" : 10028560,
# 	"src_id" : "1000001",
# 	"prefname" : "Ciudad de Mexico",
# 	"altnames" : ["Ciudad de Mexico","Mexico"],
# 	"geom" : {"type":"MultiPoint","coordinates":[[-99.13313445,19.43378643]]},
# 	"placetypes" : ["inhabited place"],
# 	"countries" : ["MX"],
# 	"province" : "Mexico",
# 	"minmax" : [1521,1808],
# 	"region" : ""
# }

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
