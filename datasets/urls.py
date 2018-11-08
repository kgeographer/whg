from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from . import views

# dataset actions
urlpatterns = [
    # url(r'^$', views.home, name="contrib_home"),

    # list for logged in user
    url(r'^$', views.dashboard, name="dashboard"),

    # upload file, validate format
    path('new', views.ds_new, name="ds_new"),

    # destroy
    # path('delete/<int:pk>', views.ds_delete, name="ds_delete"),
    path('<int:pk>delete/', views.ds_delete, name="ds_delete"),

    # edit metadata
    # path('edit/<int:pk>', views.ds_update, name="ds_edit"),
    path('<int:pk>/edit/', views.ds_update, name="ds_edit"),

    # insert file data to db
    # path('insert/<int:pk>', views.ds_insert, name="ds_insert"),
    path('<int:pk>/insert/', views.ds_insert, name="ds_insert"),

    # select authority for reconciliation
    # path('recon/<int:pk>', views.ds_recon, name="ds_recon"), # form submit
    path('<int:pk>/recon/', views.ds_recon, name="ds_recon"), # form submit

    # list places
    # path('datagrid/<str:label>', views.ds_grid, name='ds_grid'),
    path('<str:label>/datagrid/', views.ds_grid, name='ds_grid'),

    # url(r'^testmodel$', TestModelList.as_view(), name="testmodel"),
    # url(r'^testmodel_data/$', TestModelListJson.as_view(), name="testmodel_list_json"),
    # path('datagrid/<str:label>', views.DatasetGrid.as_view(), name="ds_grid"),
    # path('datagrid_data/', views.DatasetGridJson.as_view(), name="ds_grid_json"),

    # path('datagrid/<str:label>', views.ds_grid.as_view(), name='ds_grid'),

] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
