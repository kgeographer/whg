from django import template
from django.template.defaultfilters import stringfilter
import json

register = template.Library()

@register.filter
@stringfilter
def trimbrackets(value):
    """trims [ and ] from string, returns integer"""
    return int(value[1:-1])

@register.filter
def parsejson(value,key):
    """returns value for given key"""
    obj = json.loads(value.replace("'",'"'))
    return obj[key]
