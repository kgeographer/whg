# functions related to datasets app
from __future__ import absolute_import, unicode_literals

import sys, os, re, json, codecs, datetime, time
from pprint import pprint

import random
from celery.decorators import task

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

def read_delimited(infile, username):
    import csv
    result = {'format':'delimited','errors':{}}
    # required fields
    # TODO: req. fields not null or blank
    required = ['id', 'name', 'name_src', 'ccode', 'lon', 'lat']

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
        result['errors']['req'] = 'missing required column (id,name,name_src, ccode,lon,lat)'
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
