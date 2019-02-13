from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import View
import simplejson as json

from elasticsearch import Elasticsearch

class NameSuggestView(View):
    """ Returns place name suggestions """
    @staticmethod
    def get(request):
        print('in NameSuggestView',request.GET)
        """
        args in request.GET:
            [string] idx: index to be queried
            [string] search: chars to be queried for the suggest field search
            [string] doc_type: context needed to filter suggestion searches
        """
        idx = request.GET.get('idx')
        text = request.GET.get('search')
        doctype = request.GET.get('doc_type')
        q_initial = { 
            "suggest":{"suggest":{"prefix":text,"completion":{"field":"suggest"}}}
        }
        suggestions = nameSuggest(idx, doctype, q_initial)
        suggestions = [{"name":s['title'],"type":s['types'][0]['label'],"pid":s['place_id']} for s in suggestions]
        return JsonResponse(suggestions, safe=False)

def nameSuggest(idx,doctype,q_initial):
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    suggestions = []
    res = es.search(index=idx, doc_type=doctype, body=q_initial)
    hits = res['suggest']['suggest'][0]['options']
    
    if len(hits) > 0:
        for h in hits:
            hit_id = h['_id']
            print('h in nameSuggest',h)
            if 'parent' in h['_source']['relation'].keys():
                # it's a child, get siblings and add to suggestions[]
                pid = h['_source']['relation']['parent']
                q_parent = {"query":{"parent_id":{"type":"child","id":pid}}}
                res = es.search(index='whg_flat', doc_type='place', body=q_parent)
                kids = res['hits']['hits']
                for k in kids:
                    suggestions.append(k['_source'])
            else:
                # it's a parent, add to all_hits[] and get kids if any
                suggestions.append(h['_source'])
                q_parent = {"query":{"parent_id":{"type":"child","id":hit_id}}}
                res = es.search(index='whg_flat', doc_type='place', body=q_parent)
                if len(res['hits']['hits']) > 0:
                    for i in res['hits']['hits']:
                        suggestions.append(i['_source'])
        
        print(json.dumps(suggestions,indent=2))
        print('got '+str(len(suggestions))+' results, like any?\n')
    #else:
        #print('got nothing for that string, sorry!')

    return suggestions


def home(request):
    return render(request, 'search/home.html')

def advanced(request):
    print('in search/advanced() view')
    return render(request, 'search/advanced.html')

