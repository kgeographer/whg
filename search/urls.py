from django.urls import path, include
from django.conf.urls import url

from search.views import advanced, NameSuggestView, fetchArea

urlpatterns = [
    # url(r'^$', views.home, name="search_home"),
    #url(r'^$', search, name="searchy"),
    url(r'^names?$', NameSuggestView.as_view(), name='name_suggest'),
    url(r'^advanced$', advanced, name="search_adv"),


    # path('<int:product_id>/', views.detail, name='detail'),
    # path('<int:product_id>/upvote', views.upvote, name='upvote'),
    # path('create', views.create, name='create'),
]
