# search.views
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import View
import simplejson as json

from elasticsearch import Elasticsearch

def makeGeom(pid,geom):
    # TODO: account for non-point
    geomset = []
    if len(geom) > 0:    
        for g in geom:
            geomset.append(
                {"type":g['location']['type'],"coordinates":g['location']['coordinates'],"properties":{"pid": pid}}
            )
    return geomset
        
# make stuff available in autocomplete dropdown
def suggestionItem(s):
    #print('sug geom',s['geometries'])
    print('sug', s)
    item = { "name":s['title'],
             "type":s['types'][0]['label'],
             "whg_id":s['whg_id'],
             "pid":s['place_id'],
             "variants":[n for n in s['suggest']['input'] if n != s['title']],
             "dataset":s['dataset'],
             "ccodes":s['ccodes'],
             "geom": makeGeom(s['place_id'],s['geoms'])
        }
    return item
    
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
        suggestions = [ suggestionItem(s) for s in suggestions]
        return JsonResponse(suggestions, safe=False)

def nameSuggest(idx,doctype,q_initial):
    # return only parents; children will be retrieved in portal page
    # TODO: return child IDs, geometries?
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    suggestions = []
    res = es.search(index=idx, doc_type=doctype, body=q_initial)
    hits = res['suggest']['suggest'][0]['options']
    
    if len(hits) > 0:
        for h in hits:
            hit_id = h['_id']
            if 'parent' not in h['_source']['relation'].keys():
                # it's a parent, add to suggestions[]
                suggestions.append(h['_source'])
        
    return suggestions


def home(request):
    return render(request, 'search/home.html')

def advanced(request):
    print('in search/advanced() view')
    return render(request, 'search/advanced.html')

