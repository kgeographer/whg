# datasets.formset

from django import forms
from .models import Dataset, Hit


MATCHTYPES = [
    ('related','related'),
    ('close_match','closeMatch'),
    ('exact_match','exactMatch'),
    ('none','no match'),]

class HitModelForm(forms.ModelForm):
    match = forms.CharField(initial='none',widget=forms.RadioSelect(choices=MATCHTYPES))
    flag_geom = forms.BooleanField(initial=False, required=False)
    review_note = forms.CharField(required=False,
        widget=forms.Textarea(attrs={'rows':2,'cols': 80,'class':'textarea',
        'placeholder':'got notes?'})
    )
    class Meta:
        model = Hit
        # all Hit model fields
        fields = ['task_id','authority','dataset','place_id',
            'query_pass','src_id','authrecord_id','json','geom' ]
        widgets = {
            'id': forms.HiddenInput(),
            'flag_geom': forms.CheckboxInput(),
        }
# [{'task_id'(task_id), 'authority'(authority), 'dataset'(ds_label),
# 'place_id', 'authrecord_id', 'id'}]

class DatasetModelForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ('id','label','name','description','file','format','datatype',
            'delimiter','status','owner','mapbox_id','header','numrows')
        widgets = {
            'description': forms.Textarea(attrs={'rows':2,'cols': 60,'class':'textarea','placeholder':'brief description'}),
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
