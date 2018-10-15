from django.shortcuts import render

# views for static content
def home(request):
    return render(request, 'main/home.html')

def about(request):
    return render(request, 'main/about.html')

def community(request):
    return render(request, 'main/community.html')

def credits(request):
    return render(request, 'main/credits.html')

def usingapi(request):
    return render(request, 'main/usingapi.html')
