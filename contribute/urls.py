from django.urls import path, include
from django.conf.urls import url
from django.conf.urls.static import static
from django.conf import settings

from . import views

urlpatterns = [
    url(r'^$', views.home, name="contrib_home"),
    url(r'^dashboard$', views.dashboard, name="contrib_dashboard"),

    path('new', views.ds_new, name="ds_new"),
    path('edit/<int:pk>', views.ds_update, name="ds_update"),
    path('insert/<int:pk>', views.ds_insert, name="ds_insert"),
    path('delete/<int:pk>', views.ds_delete, name="ds_delete"),
    path('recon/<int:pk>', views.ds_recon, name="ds_recon"), # form submit

    # url(r'^testmodel$', TestModelList.as_view(), name="testmodel"),
    # url(r'^testmodel_data/$', TestModelListJson.as_view(), name="testmodel_list_json"),
    # path('datagrid/<str:label>', views.DatasetGrid.as_view(), name="ds_grid"),
    # path('datagrid_data/', views.DatasetGridJson.as_view(), name="ds_grid_json"),

    path('datagrid/<str:label>', views.ds_grid, name='ds_grid'),
    # path('datagrid/<str:label>', views.ds_grid.as_view(), name='ds_grid'),

] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
