from django import forms
from main.models import Dataset

class DatasetModelForm(forms.ModelForm):
    # nothing here? really?

    class Meta:
        model = Dataset
        fields = ('name', 'slug', 'user', 'file')
        # widgets = {
        #     # 'file': forms.FileInput()
        # }
