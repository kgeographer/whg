# contribute.views
from django.shortcuts import render
from main.models import Dataset

def home(request):
    return render(request, 'contribute/home.html')

def dashboard(request):
    dataset_list = Dataset.objects.filter(user=request.user.id)
    print('dataset_list',dataset_list)
    return render(request, 'contribute/dashboard.html', {'datasets':dataset_list})
