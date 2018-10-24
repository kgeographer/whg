from django.contrib import admin
from .models import Place, PlaceName, PlaceType, PlaceGeom, PlaceWhen, PlaceRelated, PlaceLink, PlaceDescription, PlaceDepiction

# Register your models here.
admin.site.register(Place)
admin.site.register(PlaceName)
admin.site.register(PlaceType)
admin.site.register(PlaceGeom)
admin.site.register(PlaceWhen)
admin.site.register(PlaceRelated)
admin.site.register(PlaceLink)
admin.site.register(PlaceDescription)
admin.site.register(PlaceDepiction)
