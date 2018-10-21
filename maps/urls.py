from django.urls import path, include
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name="maps_home"),
    url(r'^mappy$', views.mappy, name="mappy"),


    # path('<int:product_id>/', views.detail, name='detail'),
    # path('<int:product_id>/upvote', views.upvote, name='upvote'),
    # path('create', views.create, name='create'),
]
