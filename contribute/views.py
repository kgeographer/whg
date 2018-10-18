# contribute.views
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from main.models import Dataset
from .forms import DatasetModelForm
from pprint import pprint

def home(request):
    return render(request, 'contribute/home.html')

def edit(request, dataset_id):
    dataset = get_object_or_404(Dataset, id=dataset_id)
    return render(request, 'contribute/edit.html', {'dataset':dataset})

def delete(request, dataset_id):
    dataset = get_object_or_404(Dataset, id=dataset_id)
    dataset.delete()

    return HttpResponseRedirect('/contribute/dashboard')

def dashboard(request):
    dataset_list = Dataset.objects.filter(user=request.user.id).order_by('-uploaded')
    print('dataset_list',dataset_list)
    return render(request, 'contribute/dashboard.html', {'datasets':dataset_list})

def upload(request):
    print('got to views.upload()')
    if request.method == 'POST':
        form = DatasetModelForm(request.POST, request.FILES)
        pprint(locals())
        # print(form)
        if form.is_valid():
            print('form is valid')
            # file is saved
            form.save()
            return HttpResponseRedirect('/contribute/dashboard')
        else:
            print('submitted form is NOT valid')
            pprint(form.errors)
    else:
        form = DatasetModelForm()
    return render(request, 'contribute/upload.html', {'upload_form': form})
