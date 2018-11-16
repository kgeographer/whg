from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from . import views
# from datasets.views import (DatasetDetailView, DatasetCreateView,
#     DatasetUpdateView, DatasetDeleteView)

# dataset actions
app_name='datasets'
urlpatterns = [

    path('create/', views.DatasetCreateView.as_view(), name='dataset-create'),
    path('<int:id>/detail', views.DatasetDetailView.as_view(), name='dataset-detail'),
    path('<int:id>/update', views.DatasetUpdateView.as_view(), name='dataset-update'),
    path('<int:id>/delete', views.DatasetDeleteView.as_view(), name='dataset-delete'),


    # insert file data to db
    path('<int:pk>/insert/', views.ds_insert, name="ds_insert"),

    # select authority for reconciliation
    path('<int:pk>/recon/', views.ds_recon, name="ds_recon"), # form submit

    # review, validate hits
    path('<int:pk>/review/<str:tid>', views.review, name="review"),

    # list places
    path('<str:label>/datagrid/', views.ds_grid, name='ds_grid'),


] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
