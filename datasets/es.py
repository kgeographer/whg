# index dataset from database
# 7 Feb 2019
from __future__ import absolute_import, unicode_literals
import sys, os, re, json, codecs, datetime, time, csv, random
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
#from elasticsearch import Elasticsearch
#es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

dataset='dplace'
scheme='flat'
# 1428 dplace records; 1364 new, 64 into is_conflation_of
# e.g. 97829 (Calusa) into 12347200
# index dataset ('conflate','flat')
def indexDataset(dataset,scheme):
    qs = Place.objects.all().filter(dataset_id=dataset)
    count = 0
    
    if scheme=='conflate':
        def maxID():
            q={"aggs":{"max_whgid" : { "max" : { "field" : "whgid" } } } }
            res = es.search(index="whg_"+scheme, size=0, body = q)
            return int(res['aggregations']['max_whgid']['value'])   
        whgid = maxID(); print('max whgid:',whgid)  
    count_seeds = count_kids = 0
    for place in qs:
        #place=get_object_or_404(Place,id=118432) # dbp:Calusa
        #links=place.links.first().json
        # build query object
        qobj = queryObject(place)

        # if it has links, look for matches in existing
        matches = findMatch(qobj,scheme,es) if 'links' in qobj.keys() else {"scheme":scheme, "parents":[], "names":[]}
    
        if len(matches['parents']) == 0:
            if scheme=='conflate':
                whgid +=1
                seed_obj = makeSeed(place,dataset,whgid)
                try:
                    res = es.index(index=idx, doc_type='place', id=whgid, body=seed_obj.toJSON())
                    count_seeds +=1
                except:
                    print(qobj['place_id'], ' broke it')
                    print("error:", sys.exc_info()[0])
            elif scheme=='flat':
                count_seeds +=1
                child_obj = makeDoc(place,'none')
                child_obj['relation']={"name":"parent"}
                for n in child_obj['names']:
                    child_obj['suggest']['input'].append(n['toponym'])                
                res = es.index(index=idx, doc_type='place', id=place.id, body=json.dumps(child_obj))
        else:
            # 1 or more matches
            for pid in matches['parents']:
                if scheme=='conflate':
                    count_kids +=1                    
                    child_obj = makeChild(place,'none') # no parent
                    insertChildConflate(parentid,child_obj,es)
                elif scheme=='flat':
                    count_kids +=1                
                    child_obj = makeDoc(place,pid)
                    child_obj['relation']={"name":"child","parent":pid}
                    #for n in child_obj['names']:
                        #child_obj['suggest']['input'].append(n['toponym'])                                    
                    try:
                        res = es.index(index=idx,doc_type='place',id=place.id,
                            routing=1,body=json.dumps(child_obj))
                    except:
                        print('failed indexing '+str(place.id), child_obj)
                        sys.exit(sys.exc_info()[0])
                        
                    # add child's names to parent's suggest{"input":[]}
                    q_update = {
                        "script": {
                          "source": "ctx._source.suggest.input.addAll(params.names)",
                          "lang": "painless",
                          "params":{"names": matches['names']}
                        },
                        "query": {"match":{"_id": pid}}
                      }
                    try:
                        es.update_by_query(index=idx,doc_type='place',body=q_update)
                    except:
                        print('failed updating suggest for parent '+str(pid)+' from child '+str(place.id))
                        #print(sys.exc_info()[0])                            
                        
    print(str(count_seeds)+' fresh records added, '+str(count_kids)+' child records added')

def init(dataset):
    global es, idx, scheme, rows
    scheme='flat'
    idx = 'whg_'+scheme # 'conflate' or 'flat' (parent-child)

    from elasticsearch import Elasticsearch
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    q_del = {"query": {"match": {"dataset": dataset}}}
    # zap dataset from index
    try:
        res=es.delete_by_query(idx,q_del)
        print(str(res['deleted'])+' docs deleted')
    except Exception as ex:
        print(ex)
    
    indexDataset(dataset,scheme)
    