# places.urls

from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from . import views

# place actions
app_name='places'
urlpatterns = [

    # path('create/', views.AreaCreateView.as_view(), name='area-create'),
    path('<int:id>/detail', views.PlaceDetailView.as_view(), name='place-detail'),
    # path('<int:id>/update', views.AreaUpdateView.as_view(), name='area-update'),
    # path('<int:id>/delete', views.AreaDeleteView.as_view(), name='area-delete'),

] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
