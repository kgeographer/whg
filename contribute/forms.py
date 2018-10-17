from django import forms
from main.models import Dataset

class DatasetModelForm(forms.ModelForm):
    # nothing here? really?

    class Meta:
        model = Dataset
        fields = ['id','name', 'slug', 'user','upload',
            'created','modified' ]
        widgets = {
            'upload': forms.FileInput()
        }
