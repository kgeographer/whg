from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView
from django.utils.safestring import SafeString

from .models import *
from datasets.models import Dataset

class PlacePortalView(DetailView):
    # TODO: get conflated record data from ES index
    template_name = 'places/place_portal.html'

    def get_success_url(self):
        id_ = self.kwargs.get("id")
        return '/places/'+str(id_)+'/detail'

    def get_object(self):
        print('kwargs:',self.kwargs)
        id_ = self.kwargs.get("id")
        return get_object_or_404(Place, id=id_)

    def get_context_data(self, *args, **kwargs):
        context = super(PlacePortalView, self).get_context_data(*args, **kwargs)
        id_ = self.kwargs.get("id")
        place = get_object_or_404(Place, id=id_)
        spinedata = Dataset.objects.filter(id__in=[1,2])

        context['names'] = place.names.all()
        context['links'] = place.links.all()
        context['whens'] = place.whens.all()
        context['geoms'] = place.geoms.all()
        context['types'] = place.types.all()
        context['related'] = place.related.all()
        context['descriptions'] = place.descriptions.all()
        context['depictions'] = place.depictions.all()

        context['spine'] = spinedata
        print('place context',str(context))
        return context

class PlaceContribView(DetailView):
    template_name = 'places/place_contrib.html'

    def get_success_url(self):
        id_ = self.kwargs.get("id")
        return '/contrib/'+str(id_)+'/detail'

    def get_object(self):
        print('kwargs:',self.kwargs)
        id_ = self.kwargs.get("id")
        return get_object_or_404(Place, id=id_)

    def get_context_data(self, *args, **kwargs):
        context = super(PlaceContribView, self).get_context_data(*args, **kwargs)
        id_ = self.kwargs.get("id")
        place = get_object_or_404(Place, id=id_)
        spinedata = Dataset.objects.filter(id__in=[1,2])

        context['names'] = place.names.all()
        context['links'] = place.links.all()
        context['whens'] = place.whens.all()
        context['geoms'] = place.geoms.all()
        context['types'] = place.types.all()
        context['related'] = place.related.all()
        context['descriptions'] = place.descriptions.all()
        context['depictions'] = place.depictions.all()

        context['spine'] = spinedata
        print('place context',str(context))
        return context
