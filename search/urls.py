from django.urls import path, include
from django.conf.urls import url

from search.views import advanced, NameSuggestView, fetchArea, FeatureContextView

urlpatterns = [
    # url(r'^$', views.home, name="search_home"),
    #url(r'^$', search, name="searchy"),
    url(r'^names?$', NameSuggestView.as_view(), name='name_suggest'),
    url(r'^features?$', FeatureContextView.as_view(), name='feature_context'),
    url(r'^advanced$', advanced, name="search_adv"),
]
