# index dataset from database
# 7 Feb 2019
from __future__ import absolute_import, unicode_literals
import sys, os, re, json, codecs, datetime, time, csv, random
from elasticsearch import Elasticsearch
from geopy import distance
import shapely.geometry
from pprint import pprint

from celery.decorators import task
from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect

from areas.models import Area
from datasets.es_utils import * # 
from datasets.models import Dataset, Hit
from datasets.regions import regions as region_hash
from datasets.utils import roundy, fixName, classy, bestParent, elapsed, hully
from places.models import Place
##
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

dataset='dplace'
scheme='conflate'
# 1428 dplace records; 1364 new, 64 into is_conflation_of
# e.g. 97829 (Calusa) into 12347200
# index dataset ('conflate','flat')
def indexDataset(dataset,scheme):
    qs = Place.objects.all().filter(dataset_id=dataset)
    count = 0
    
    def maxID():
        q={"aggs":{"max_whgid" : { "max" : { "field" : "whgid" } } } }
        res = es.search(index="whg_"+scheme, size=0, body = q)
        return int(res['aggregations']['max_whgid']['value'])   
    whgid = maxID(); print('max whgid:',whgid)  
    count_seeds = count_kids = 0
    for place in qs:
        place=get_object_or_404(Place,id=97829) # dbp:Calusa
        links=place.links.first().json
        
        # build query object
        qobj = queryObject(place)
        
        # if it has links, look for matches in existing
        matches = findMatch(qobj,scheme,es) if 'links' in qobj.keys() else {"scheme":scheme, "whgids":[]}
    
        if len(matches['whgids']) == 0:
            # no matches -> make seed record + first child
            whgid +=1
            seed_obj = makeSeed(place,dataset,whgid)
            # add
            try:
                res = es.index(index='whg_'+scheme, doc_type='place', id=whgid, body=seed_obj.toJSON())
                count_seeds +=1
            except:
                print(doc['place_id'], ' broke it')
                print("error:", sys.exc_info()[0])                
        else:
            count_kids +=1
            # 1 or more matches
            for parentid in matches['whgids']:
                #print('insert '+str(place.id)+' into each of these:'+str(m))
                child_obj = makeChildConflate(place) if scheme=='conflate' \
                    else makeChildFlat(place, parentid)
                print(child_obj)
            #insertChild(parent_id, child_obj)
    print(str(count_seeds)+' seeds added, '+str(count_kids)+' kids to be added')
#index_dataset('dplace')