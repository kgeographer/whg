# whg.builtins
from django import template
# from django.utils.html import escape
# from django.utils.safestring import mark_safe

register = template.Library()

# {{ form.json|get:"_source" }}

@register.filter(name='get')
def get(d, k):
    print('get(d,k):',d,k)
    return d.get(k, None)
