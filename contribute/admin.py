from django.contrib import admin
from .models import Dataset, Link, Hit, Authority


admin.site.register(Dataset)
admin.site.register(Link)
admin.site.register(Hit)
admin.site.register(Authority)
