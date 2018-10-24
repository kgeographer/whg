# functions related to contribute apps
import sys, os, re, json, codecs, datetime, time
from pprint import pprint

def read_csv(infile):
    import csv
    #result = {'format':'csv','errors':{'rowlength':[]}}
    result = {'format':'csv','errors':{}}
    required = ['id', 'title', 'ccode', 'lon', 'lat']

    # learn delimiter
    dialect = csv.Sniffer().sniff(infile.read(1024))
    result['delimiter'] = 'tab' if dialect.delimiter == '\t' else dialect.delimiter

    reader = csv.reader(infile, dialect)
    result['count'] = sum(1 for row in reader)

    # get & test header
    infile.seek(0)
    header = next(reader, None) #.split(dialect.delimiter)
    result['cols'] = header

    if not len(set(header) & set(required)) == 5:
        result['errors']['req'] = 'missing required column (id,title,ccode,lon,lat)'
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
        feature = {
            'type':'Feature',
            'geometry': {'type':'Point',
                         'coordinates':[ float(r[header.index('lon')]), float(r[header.index('lat')]) ]},
            'properties': {'id':r[header.index('id')], 'title': r[header.index('title')]}
        }
        props = set(header) - set(required)
        for p in props:
            feature['properties'][p] = r[header.index(p)]
        geometries.append(feature)

    if len(result['errors'].keys()) == 0:
        # add geometries
        result['geom'] = {"type":"FeatureCollection", "features":geometries}
        print('looks ok to me, go ahead and map geom')
    else:
        print('got errors')
    return result

def read_lpf(infile):
    return 'reached tasks.read_lpf()'
