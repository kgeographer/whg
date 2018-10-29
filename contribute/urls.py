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

    # url(r'^testmodel$', TestModelList.as_view(), name="testmodel"),
    # url(r'^testmodel_data/$', TestModelListJson.as_view(), name="testmodel_list_json"),
    # path('datagrid/<str:label>', views.DatasetGrid.as_view(), name="ds_grid"),
    # path('datagrid_data/', views.DatasetGridJson.as_view(), name="ds_grid_json"),

    path('datagrid/<str:label>', views.ds_grid, name='ds_grid'),
    # path('datagrid/<str:label>', views.ds_grid.as_view(), name='ds_grid'),

] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

    # url(r'^upload$', views.upload, name="contrib_upload"),
    # path('<int:dataset_id>/delete', views.delete, name="contrib_delete"),
    # path('<int:dataset_id>/edit', views.edit, name="contrib_edit"),

    # path('<int:product_id>/', views.detail, name='detail'),
    # path('<int:product_id>/upvote', views.upvote, name='upvote'),
    # path('create', views.create, name='create'),
