# contribute.views

from django.shortcuts import render

def home(request):
    return render(request, 'contribute/home.html')

def dashboard(request):
    return render(request, 'contribute/dashboard.html')
