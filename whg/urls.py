from django.contrib import admin
from django.urls import path
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from main import views

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    url(r'^$', views.home, name="home"),

    # apps
    path('search/', include('search.urls')),
    path('maps/', include('maps.urls')),
    path('contribute/', include('contribute.urls')),

    # static content
    url(r'^usingapi/$', views.usingapi, name="usingapi"),
    url(r'^community/$', views.community, name="community"),
    url(r'^about/$', views.about, name="about"),
    url(r'^credits/$', views.credits, name="credits"),

    path('api/', include('api.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
