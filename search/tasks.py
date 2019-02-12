# some queries 12 Feb 2019
import json
from elasticsearch import Elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

idx="whg_flat"

def findName():
    name = input('name [Calusa]: ') or 'Calusa'
    #print('name: ',name)
    all_hits=[]
    q_suggest = { 
        "suggest":{"suggest":{"prefix":name,"completion":{"field":"suggest"}}}
    }
    res = es.search(index=idx, doc_type='place', body=q_suggest)
    # build all_hits[]
    hits = res['suggest']['suggest'][0]['options']
    #print('hits:',hits)
    if len(hits) > 0:
        for h in hits:
            hit_id = h['_id']
            if 'parent' in h['_source']['relation'].keys():
                # it's a child, get siblings and add to all_hits[]
                pid = h['_source']['relation']['parent']
                #print('child, has parent:',pid)
                q_parent = {"query":{"parent_id":{"type":"child","id":pid}}}
                res = es.search(index='whg_flat', doc_type='place', body=q_parent)
                kids = res['hits']['hits']
                for k in kids:
                    all_hits.append(k['_source'])
            else:
                # it's a parent, add to all_hits[] and get kids if any
                all_hits.append(h['_source'])
                q_parent = {"query":{"parent_id":{"type":"child","id":hit_id}}}
                res = es.search(index='whg_flat', doc_type='place', body=q_parent)
                if len(res['hits']['hits']) > 0:
                    #print('parent has kids:',str(res['hits']))
                    for i in res['hits']['hits']:
                        all_hits.append(i['_source'])
        print(json.dumps(all_hits,indent=2))
        print('got '+str(len(all_hits))+' results, like any?\n')
    else:
        print('got nothing for that string, sorry!')

findName()