from django.contrib import admin
from .models import Place, Source, PlaceName, PlaceType, PlaceGeom, PlaceWhen, PlaceRelated, PlaceLink, PlaceDescription, PlaceDepiction

# appear in admin
admin.site.register(Place)

class SourceAdmin(admin.ModelAdmin):
    list_display = ('owner','src_id', 'label', 'uri')
admin.site.register(Source,SourceAdmin)

admin.site.register(PlaceName)
admin.site.register(PlaceType)
admin.site.register(PlaceGeom)
admin.site.register(PlaceWhen)
admin.site.register(PlaceRelated)
admin.site.register(PlaceLink)
admin.site.register(PlaceDescription)
admin.site.register(PlaceDepiction)
