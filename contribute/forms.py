# contribute.formset

from django import forms
from main.models import Dataset

class DatasetModelForm(forms.ModelForm):
    # nothing here? really?

    class Meta:
        model = Dataset
        fields = ('label','name','description','file','format','datatype',
            'status','owner','mapbox_id')
        widgets = {
            'description': forms.Textarea(attrs={'rows':2,'cols': 60,'class':'textarea','placeholder':'brief description'}),
            'format': forms.Select(),
            'datatype': forms.Select()
        }

    def __init__(self, *args, **kwargs):
        super(DatasetModelForm, self).__init__(*args, **kwargs)
        # self.fields['mapbox_id'].required = False
