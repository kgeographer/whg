from django import forms
from django.db import models
# from leaflet.forms.widgets import LeafletWidget
from .models import Area

class AreaModelForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('id','type','owner','title','description','ccodes','geojson')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':2,'cols': 30,'class':'textarea',
                'placeholder':'brief description'
            }),
            # 'geom': LeafletWidget(),
            'geojson': forms.Textarea(attrs={
                'rows':3,'cols': 30,'class':'textarea',
                'placeholder':'GeoJSON, from countries for now'
            }),
        }


    def __init__(self, *args, **kwargs):
        super(AreaModelForm, self).__init__(*args, **kwargs)

class AreaDetailModelForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('id','type','owner','title','description','ccodes','geojson')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':1,'cols': 60,'class':'textarea','placeholder':'brief description'}),
        }

    def __init__(self, *args, **kwargs):
        super(AreaDetailModelForm, self).__init__(*args, **kwargs)
