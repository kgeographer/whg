# contribute model field value choices

FORMATS = [
    ('csv', 'CSV'),
    ('lpf', 'Linked Places format'),
]

DATATYPES = [
    ('place', 'Places'),
    ('anno', 'Annotations'),
    ('source', 'Sources')
]

STATUS = [
    ('format_error', 'Invalid format'),
    ('format_ok', 'Valid format'),
    ('uploaded', 'Uploaded'),
    ('ready', 'Ready for submittal'),
    ('accepted', 'Accepted'),
]

AUTHORITIES = [
    ('tgn','Getty TGN'),
    ('dbp','DBpedia'),
    ('gn','Geonames'),
    ('wd','Wikidata'),
    ('spine','WHG Spine'),
]

MATCHTYPES = {
    ('exact','exactMatch'),
    ('close','closeMatch'),
    ('related','related'),
}
