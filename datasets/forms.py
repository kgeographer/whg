# datasets.formset

from django import forms
from django.db import models
from .models import Dataset, Hit

MATCHTYPES = [
    ('related','related'),
    ('close_match','closeMatch'),
    ('exact_match','exactMatch'),
    ('none','no match'),]

class HitModelForm(forms.ModelForm):
    #'id','authrecord_id','json','query_pass','score'
    match = forms.CharField(initial='none',
        widget=forms.RadioSelect(choices=MATCHTYPES))
    flag_geom = forms.BooleanField(initial=False, required=False)
    review_note = forms.CharField(required=False,
        widget=forms.Textarea(attrs={'rows':2,'cols': 80,'class':'textarea',
        'placeholder':'got notes?'})
    )
    # authrecord_id = forms.CharField(max_length=255, required=False)
    id = forms.CharField(max_length=255, required=False)
    # place_id = forms.CharField(max_length=255, required=False)

    class Meta:
        model = Hit
        fields = ['id','authrecord_id','json', 'query_pass', 'score' ]
        # all Hit model fields
        # fields = ['task_id','authority','dataset','place_id',
        #     'query_pass','src_id','authrecord_id','json','geom' ]
        widgets = {
            'id': forms.HiddenInput(),
            'authrecord_id': forms.HiddenInput(),
            # 'place_id': forms.HiddenInput(),
            'json': forms.HiddenInput(),
            'flag_geom': forms.CheckboxInput(),
        }

class DatasetDetailModelForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ('id','name','description','mapbox_id')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':1,'cols': 60,'class':'textarea','placeholder':'brief description'}),
        }

    def __init__(self, *args, **kwargs):
        super(DatasetDetailModelForm, self).__init__(*args, **kwargs)

class DatasetModelForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ('id','label','name','description','file','format','datatype',
            'delimiter','status','owner','mapbox_id','header','numrows','spine','uri_base')
        widgets = {
            'description': forms.Textarea(attrs={
                'rows':2,'cols': 60,'class':'textarea',
                'placeholder':'brief description'}),
            'format': forms.Select(),
            'datatype': forms.Select()
        }
        initial = {'format': 'delimited', 'datatype': 'places'}

    def unique_label(self, *args, **kwargs):
        label = self.cleaned_content['label']
        # TODO: test uniqueness somehow

    def __init__(self, *args, **kwargs):
        self.format = 'delimited'
        self.datatype = 'place'
        super(DatasetModelForm, self).__init__(*args, **kwargs)
