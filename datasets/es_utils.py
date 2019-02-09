# es_utils.py 7 Feb 2019
# misc supporting eleasticsearch tasks (es.py)

class SeedPlace(object):
    def __init__(self, whgid, place_id, dataset, src_id, title):
        self.whgid = whgid
        self.representative_title = title
        self.seed_dataset = dataset
        self.representative_point = []
        self.representative_shape = []
        self.suggest = {"input":[]}
        self.minmax = []
        self.is_conflation_of = []

    def __str__(self):
        import json
        #return str(self.__class__) + ": " + str(self.__dict__)    
        return json.dumps(self.__dict__)

    def toJSON(self):
        import json
        #return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=2)    
        return json.dumps(self, default=jsonDefault, sort_keys=True, indent=2)            

def uriMaker(place):
    from django.shortcuts import get_object_or_404
    ds = get_object_or_404(Dataset,id=place.dataset.id)
    return ds.uri_base
    
def findMatch(qobj,scheme,es):
    matches = {"scheme":scheme, "whgids":[]}
    q_links = {"query": { 
        "bool": {
            "must": [
                {"nested": {
                    "path": "is_conflation_of",
                    "query": {
                        "nested" : {
                            "path" :  "is_conflation_of.links",
                            "query" : {
                                "terms": {
                                    "is_conflation_of.links.identifier": qobj['links'] }}
                    }}
                }}
            ]
        }
    }}
    
    if len(qobj['links']) > 0: # if links, terms query
        res = es.search(index='whg_'+scheme, doc_type='place', body=q_links)
        hits = res['hits']['hits']
        if len(hits) == 0:
            print('no hits, run makeSeed()')
            # create seed (and/or parent+child)
        elif len(hits) > 0:
            for h in hits:
                matches['whgids'].append(h['_source']['whgid'])
    return matches

def makeChildConflate(place):
    cc_obj = {
            "place_id": place.id,
            "dataset": place.dataset.label,
            "src_id": place.src_id,
            "title": place.title,
            "uri": uriMaker(place),
            "ccodes": place.ccodes,
            "names": parsePlace(place,'names'),
            "types": parsePlace(place,'types'),
            "links": parsePlace(place,'links'),
            "geoms": parsePlace(place,'geoms'),
            "descriptions": parsePlace(place,'descriptions')
            #"relations": [],
            #"depictions": [], 
            #"timespans": []
        }
    return cc_obj


def makeSeed(place, dataset, whgid):
    # whgid, place_id, dataset, src_id, title
    sobj = SeedPlace(whgid, place.id, dataset, place.src_id, place.title )
    
    # top level properties
    # TODO: geometry, defer for now
    #if len(place.geoms.all()) > 0:
        #for g in place.geoms.all():
            #if g['type'] in ('Point'):
                ## aggregate in MultiPoint
                #sobj['representative_point'] = place.geoms.first().json
            #elif g['type'] == 'MultiLineString':
                ## aggregate
                #sobj['representative_shape'] = hully(ls_agg)
            #elif g['type'] == 'MultiPolygon':
                ## aggregate
                #sobj['representative_shape'] = hully(poly_agg)
                    
    # pull from name.json
    for n in place.names.all():
        sobj.suggest['input'].append(n.json['toponym'])
    
    # no place_when data yet
    if len(place.whens.all()) > 0:
        sobj['minmax'] = []
    
    sobj.is_conflation_of.append(makeChildConflate(place))
    
    # TODO update sobj['suggest']['input']
    # TODO update sobj['minmax']
    # TODO ?? update global geometry
    
    return sobj


def insertChild(parent_id, child_obj):
    # select parent, add child to is_conflation_of
    print('added ',child_obj,' to ',parent_id)
            
def jsonDefault(value):
    import datetime
    if isinstance(value, datetime.date):
        return dict(year=value.year, month=value.month, day=value.day)
    else:
        return value.__dict__
    
def parsePlace(place,attr):
    qs = eval('place.'+attr+'.all()')
    arr = []
    for obj in qs:
        arr.append(obj.json)
    return arr
    
def deleteDocs(ids):
    from elasticsearch import Elasticsearch
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    for i in ids:
        try:
            es.delete(index='whg', doc_type='place', id=i)
        except:
            print('failed delete for: ',id)
            pass
        
def deleteKids(ids):
    from elasticsearch import Elasticsearch
    {"nested": {
            "path": "is_conflation_of",
            "query": 
              {"nested" : {
                "path" :  "is_conflation_of.types",
                "query" : {"terms": {"is_conflation_of.place_id": ids}}
                }
              }
          }}    
    q={"query": {"terms": { "":ds }}}
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    for i in ids:
        try:
            es.delete(index='whg', doc_type='place', id=i)
        except:
            print('failed delete for: ',id)
            pass

def deleteDataset(ds):
    q={"query": {"match": { "seed_dataset":ds }}}
    try:
        es.delete(es_index='whg', doc_type='place', body=q)
    except:
        print('failed delete for: ',ds)
        pass
    



def queryObject(place):
    qobj = {"place_id":place.id,"src_id":place.src_id,"title":place.title}
    variants=[]; geoms=[]; types=[]; ccodes=[]; parents=[]; links=[]
    
    # ccodes (2-letter iso codes)
    for c in place.ccodes:
        ccodes.append(c)
    qobj['ccodes'] = place.ccodes
    
    # types (Getty AAT identifiers)
    for t in place.types.all():
        types.append(t.json['identifier'])
    qobj['types'] = types
    
    # names
    for name in place.names.all():
        variants.append(name.toponym)
    qobj['variants'] = variants
    
    # parents
    for rel in place.related.all():
        if rel.json['relation_type'] == 'gvp:broaderPartitive':
            parents.append(rel.json['label'])
    qobj['parents'] = parents
    
    # links
    if len(place.links.all()) > 0:
        for l in place.links.all():
            links.append(l.json['identifier'])
        qobj['links'] = links
    
    # geoms
    if len(place.geoms.all()) > 0:
        geom = place.geoms.all()[0].json
        if geom['type'] in ('Point','MultiPolygon'):
            qobj['geom'] = place.geoms.first().json
        elif geom['type'] == 'MultiLineString':
            qobj['geom'] = hully(geom)
    
    return qobj

