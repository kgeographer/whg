from django import forms
from django.db import models
from .models import Area

class AreaDetailModelForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('id','title','description','ccodes','geom')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':1,'cols': 60,'class':'textarea','placeholder':'brief description'}),
        }

    def __init__(self, *args, **kwargs):
        super(AreaDetailModelForm, self).__init__(*args, **kwargs)

class AreaModelForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('id','owner','title','description','ccodes','geom')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':1,'cols': 40,'class':'textarea',
                'placeholder':'brief description'
            }),
            'geom': forms.Textarea(attrs={
                'rows':3,'cols': 40,'class':'textarea',
                'placeholder':'GeoJSON, from countries for now'
            }),
        }
        # initial = {'format': 'delimited', 'datatype': 'places'}


    def __init__(self, *args, **kwargs):
        # self.format = 'delimited'
        super(AreaModelForm, self).__init__(*args, **kwargs)
