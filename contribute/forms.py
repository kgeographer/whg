from django import forms
from main.models import Dataset

class DatasetModelForm(forms.ModelForm):
    # nothing here? really?

    class Meta:
        model = Dataset
        fields = ('name', 'slug', 'user', 'file', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows':3,'cols': 80,'class':'textarea',
        'placeholder':'brief description'})
        }
