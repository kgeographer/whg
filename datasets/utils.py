import codecs, datetime, sys
import simplejson as json
from shapely import wkt
from shapely.geometry import MultiLineString, mapping
from datasets.static.hashes import aat, parents

def aat_lookup(id):
    try:
        label = aat.types[id]['term_full']
        return label
    except:
        print(id,' broke it')
        print("error:", sys.exc_info()[0])        

def hully(g_list):
    from django.contrib.gis.geos import GEOSGeometry
    if g_list[0]['type'] == 'Point':
        # 1 or more points => make buffer; width 1 = ~200km @ 20deg lat
        hull=json.loads(GeometryCollection([GEOSGeometry(json.dumps(g)) for g in g_list]).buffer(1).geojson)
    else:
        # now only linestrings and multiple multipolygons -> simple convex_hull (unions are precise but bigger)
        hull=json.loads(GeometryCollection([GEOSGeometry(json.dumps(g)) for g in g_list]).convex_hull.geojson)
        #union=json.loads(GeometryCollection([GEOSGeometry(json.dumps(g)) for g in g_list]).unary_union.geojson)
    return hull
    
def parse_wkt(g):
    gw = wkt.loads(g)
    feature = mapping(gw)
    print('wkt, feature',g, feature)
    return feature
    
def myteam(me):
    myteam=[]
    for g in me.groups.all():
        for u in g.user_set.all():
            myteam.append(u)
    return myteam

def parsejson(value,key):
    """returns value for given key"""
    obj = json.loads(value.replace("'",'"'))
    return obj[key]

def elapsed(delta):
    minutes, seconds = divmod(delta.seconds, 60)
    return '{:02}:{:02}'.format(int(minutes), int(seconds))

def bestParent(qobj, flag=False):
    # TODO: region only applicable for black, right?
    #global parent_hash
    best = []
    # merge parent country/ies & parents
    if len(qobj['countries']) > 0:
        for c in qobj['countries']:
            best.append(parents.ccodes[0][c]['tgnlabel'])
    if len(qobj['parents']) > 0:
        for p in qobj['parents']:
            best.append(p)
    if len(best) == 0:
        best = ['World']
    return best

def roundy(x, direct="up", base=10):
    import math
    if direct == "down":
        return int(math.ceil(x / 10.0)) * 10 - base
    else:
        return int(math.ceil(x / 10.0)) * 10

def fixName(toponym):
    import re
    search_name = toponym
    r1 = re.compile(r"(.*?), Gulf of")
    r2 = re.compile(r"(.*?), Sea of")
    r3 = re.compile(r"(.*?), Cape")
    r4 = re.compile(r"^'")
    if bool(re.search(r1,toponym)):
        search_name = "Gulf of " + re.search(r1,toponym).group(1)
    if bool(re.search(r2,toponym)):
        search_name = "Sea of " + re.search(r2,toponym).group(1)
    if bool(re.search(r3,toponym)):
        search_name = "Cape " + re.search(r3,toponym).group(1)
    if bool(re.search(r4,toponym)):
        search_name = toponym[1:]
    return search_name if search_name != toponym else toponym

# in: list of Black atlas place types
# returns list of equivalent classes or types for {gaz}
def classy(gaz, typeArray):
    import codecs, json
    #print(typeArray)
    types = []
    finhash = codecs.open('../data/feature-classes.json', 'r', 'utf8')
    classes = json.loads(finhash.read())
    finhash.close()
    if gaz == 'gn':
        t = classes['geonames']
        default = 'P'
        for k,v in t.items():
            if not set(typeArray).isdisjoint(t[k]):
                types.append(k)
            else:
                types.append(default)
    elif gaz == 'tgn':
        t = classes['tgn']
        default = 'inhabited places' # inhabited places
        # if 'settlement' exclude others
        typeArray = ['settlement'] if 'settlement' in typeArray else typeArray
        # if 'admin1' (US states) exclude others
        typeArray = ['admin1'] if 'admin1' in typeArray else typeArray
        for k,v in t.items():
            if not set(typeArray).isdisjoint(t[k]):
                types.append(k)
            else:
                types.append(default)
    elif gaz == "dbp":
        t = classes['dbpedia']
        default = 'Place'
        for k,v in t.items():
            # is any Black type in dbp array?
            # TOD: this is crap logic, fix it
            if not set(typeArray).isdisjoint(t[k]):
                types.append(k)
            #else:
                #types.append(default)
    if len(types) == 0:
        types.append(default)
    return list(set(types))
