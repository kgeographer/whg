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
from datasets.es_utils import * # query_object, make_seed, make_child
from datasets.models import Dataset, Hit
from datasets.regions import regions as region_hash
from datasets.utils import roundy, fixName, classy, bestParent, elapsed, hully
from places.models import Place
##
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

def max_id():
    q={"aggs":{"max_whgid" : { "max" : { "field" : "whgid" } } } }
    res = es.search(index="whg", size=0, body = q)
    return int(res['aggregations']['max_whgid']['value'])

# index dataset
def index_dataset(dataset):
    qs = Place.objects.all().filter(dataset_id=dataset)
    count = 0
    whgid = max_id()    
    # TODO: confirm it doesn't exist
    for place in qs:
        # build query object
        qobj = query_object(place)
        
        # is there a record for it?
        # matches = find_match(qobj)
        matches = [] # empty for now
    
        if len(matches) == 0:
            # no match, make seed record + first child
            whgid +=1
            seed_obj = make_seed(place,dataset,whgid)
            # add
            try:
                res = es.index(index='whg', doc_type='place', id=whgid, body=seed_obj.toJSON())
            except:
                print(doc['place_id'], ' broke it')
                print("error:", sys.exc_info()[0])                
        else:
            # TODO: if match, insert as child
            child_obj = make_child(place, dataset)
            # parse matches[] for parent_id
            insert_child(parent_id, child_obj)
    
#index_dataset('dplace')