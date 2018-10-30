from django.shortcuts import render, redirect

# Create your views here.
def home(request):
    return render(request, 'search/home.html')

def advanced(request):
    print('in search/advanced() view')
    return render(request, 'search/advanced.html')

def search(request):
    print('execute search task w/',request)
    return render(request, 'main/home.html')
