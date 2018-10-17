# contribute.views
from django.http import HttpResponseRedirect
from django.shortcuts import render
from main.models import Dataset
from .forms import DatasetModelForm

def home(request):
    return render(request, 'contribute/home.html')

def dashboard(request):
    dataset_list = Dataset.objects.filter(user=request.user.id)
    print('dataset_list',dataset_list)
    return render(request, 'contribute/dashboard.html', {'datasets':dataset_list})

def upload(request):
    if request.method == 'POST':
        form = DatasetModelForm(request.POST, request.FILES)
        if form.is_valid():
            # file is saved
            form.save()
            return HttpResponseRedirect('/contribute/upload')
    else:
        form = DatasetModelForm()
    return render(request, 'upload.html', {'upload_form': form})
