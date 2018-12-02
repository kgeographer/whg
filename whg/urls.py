from django.contrib import admin
from django.urls import path
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from main import views
# from datasets.views import dashboard
from datasets.views import DatasetListView

from django.views.generic.base import TemplateView
from django.contrib import admin
from django.urls import include, path

app_name='main'
urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name="main/home.html"), name="home"),

    # apps
    path('search/', include('search.urls')),
    path('maps/', include('maps.urls')),
    path('datasets/', include('datasets.urls')),
    path('dashboard/', DatasetListView.as_view(), name='dashboard'),

    # static content
    url(r'^contributing/$', TemplateView.as_view(template_name="main/contributing.html"), name="contributing"),
    url(r'^usingapi/$', TemplateView.as_view(template_name="main/usingapi.html"), name="usingapi"),
    url(r'^community/$', TemplateView.as_view(template_name="main/community.html"), name="community"),
    url(r'^about/$', TemplateView.as_view(template_name="main/about.html"), name="about"),
    url(r'^credits/$', TemplateView.as_view(template_name="main/credits.html"), name="credits"),
    url(r'^testy/$', TemplateView.as_view(template_name="main/css-bs.html"), name="testy"),

    path('api/', include('api.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
