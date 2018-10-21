from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'maps/home.html')

def mappy(request):
    return render(request, 'maps/mappy.html')
