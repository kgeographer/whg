from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'search/home.html')

def advanced(request):
    print('in search/advanced() view')
    return render(request, 'search/advanced.html')
