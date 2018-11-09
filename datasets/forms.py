# dataasets.formset

from django import forms
from main.models import Dataset

class DatasetModelForm(forms.ModelForm):
    # nothing here? really?

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

    def __init__(self, *args, **kwargs):
        self.format = 'delimited'
        self.datatype = 'place'
        super(DatasetModelForm, self).__init__(*args, **kwargs)
