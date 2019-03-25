# datasets/es_black.py; 24 Mar 2019
# initialize whg index with black; same as datasets.tasks.align_whg()??

from datasets.es_utils import * 
def placeFlat(doc,whg_id):
  from es_utils import IndexedPlaceFlat    
  from shapely.geometry import Point, MultiPoint
  ip = IndexedPlaceFlat(whg_id, doc['place_id'], 'black', doc['src_id'], doc['title'], doc['uri'])

  # suggest
  ip.suggest['input'] = [n['toponym'] for n in doc['names']] 

  # ccodes
  try:
    ip.ccodes = doc['ccodes']
  except:
    pass

  # names (toponym, lang)
  ip.names = [{'toponym':n['toponym'],'lang':n['lang']}
                for n in doc['names']]

  # types(id, label, sourceLabel)
  try:
    ip.types = [{
          'identifier':t['identifier'],
            'label':t['label'],
            'src_label':t['src_label']}
                    for t in doc['types']]
  except:
    print(doc['place_id'], ' broke it')

  # geometries; tweak format for ES geo_shape
  if doc['geometries'] != [None]:
    for g in doc['geometries']:
      geom = {"location":{
              "type":g['type'],
                    "coordinates":g['coordinates']},
                    # reverse lat/lon to lon/lat here
                    #"coordinates":[g['coordinates'][1],g['coordinates'][0]]},
                    "citation":g['citation'],
                    "geowkt":g['geowkt']}
      ip.geoms.append(geom)
    c=MultiPoint([tuple(g['coordinates']) for g in doc['geometries']]).representative_point()
    ip.representative_point = [c.x,c.y]
  else:
    ip.geoms = []

  # links(type, uri)
  ip.links = [{'type':l['type'],'identifier':l['identifier']}
                for l in doc['links']] if doc['links'] != [None] else []

  # timespans(start, end -> in, earliest, latest)
  ip.timespans = [{'start':t['start'],'end':t['end']}
                    for t in doc['timespans']]

  # descriptions(id, short, lang)
  ip.descriptions = [{'id':d['id'],'value':d['value'],'lang':d['lang']}
                       for d in doc['descriptions']] if doc['descriptions'] != [None] else []

  # compute minmax
  starts = [t['start'] for t in doc['timespans']]
  ends = [t['end'] for t in doc['timespans']]
  ip.minmax = {'start':min(starts), 'end':max(ends)}

  return ip

def indexPlaces(rows):
  import os, sys, json, time, datetime
  idx = 'whg'
  count = 0
  start = time.time()
  whg_id = 12345677 

  #for x in range(len(rows)):
  for x in range(300):
    doc=json.loads(rows[x].replace('\\\\','\\'))
    whg_id +=1
    # build an indexed place object (ip)
    ip = placeFlat(doc,whg_id) 

    # check whether place exists; add as child or parent 
    try:
      res = es.index(
        index=idx, 
          doc_type='place', 
            id=whg_id, 
            body=json.loads(ip.toJSON()))
      count +=1
    except:
      print(doc['place_id'], ' broke it')
      print("error:", sys.exc_info())
      
  end = time.time()
  print(int((end - start)/60), "min. elapsed")
  print(count,'records processed')
  print('last whgid:', whg_id)

def init():
  global es, idx, rows
  idx = 'whg'

  import os, codecs, time, datetime
  os.chdir('/Users/karlg/Documents/Repos/_whgdata')

  from elasticsearch import Elasticsearch
  es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

  # read from file for black, all others from db
  infile = codecs.open('pyin/spine-black-20190204.jsonl', 'r', 'utf8')
  rows = infile.readlines()

  mappings = codecs.open('data/elastic/mappings/mappings_whg.json', 'r', 'utf8').read()

  # zap existing if exists, re-create
  try:
    es.indices.delete(idx)
  except Exception as ex:
    print(ex)
  try:
    es.indices.create(index=idx, ignore=400, body=mappings)
    print ('index "'+idx+'" created')
  except Exception as ex:
    print(ex)

init()