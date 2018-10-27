from django.contrib import admin
from .models import Dataset, Link, Hit, Authority

class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'name', 'format', 'datatype')
admin.site.register(Dataset,DatasetAdmin)

admin.site.register(Link)
admin.site.register(Hit)
admin.site.register(Authority)
