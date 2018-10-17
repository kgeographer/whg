from django.urls import path, include
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name="contrib_home"),
    url(r'^dashboard$', views.dashboard, name="contrib_dashboard"),
    url(r'^upload$', views.upload, name="contrib_upload"),

    # path('<int:product_id>/', views.detail, name='detail'),
    # path('<int:product_id>/upvote', views.upvote, name='upvote'),
    # path('create', views.create, name='create'),
]
