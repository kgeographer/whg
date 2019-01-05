import codecs, json, datetime
fin = codecs.open('whg/static/js/parents.json', 'r', 'utf8')
parent_hash = json.loads(fin.read())
fin.close()

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
    global parent_hash

    if len(qobj['countries']) > 0:
        best = parent_hash['ccodes'][qobj['countries'][0]]['tgnlabel']
    elif len(qobj['parents']) > 0:
        best = qobj['parents'][0]
    elif len(qobj['regions']) > 0:
        best = parent_hash['regions'][qobj['region']]['tgnlabel']
    else:
        best = 'World'
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
