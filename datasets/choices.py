# datasets model field value choices

FORMATS = [
    ('delimited', 'Delimited'),
    ('lpf', 'Linked Places (JSON-LD)'),
]

DATATYPES = [
    ('place', 'Places'),
    ('anno', 'Annotations'),
    ('source', 'Sources')
]

STATUS = [
    ('format_error', 'Invalid format'),
    ('format_ok', 'Valid format'),
    ('inserted', 'Data inserted'),
    ('uploaded', 'File uploaded'),
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
