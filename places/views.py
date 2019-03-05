from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView
from django.utils.safestring import SafeString
from elasticsearch import Elasticsearch
import simplejson as json

from .models import *
from datasets.models import Dataset

class PlacePortalView(DetailView):
    # TODO: get conflated record data from ES index
    template_name = 'places/place_portal.html'

    def get_success_url(self):
        id_ = self.kwargs.get("id")
        return '/places/'+str(id_)+'/detail'

    def get_object(self):
        print('args',self.args,'kwargs:',self.kwargs)
        id_ = self.kwargs.get("id")
        return get_object_or_404(Place, id=id_)

    def get_context_data(self, *args, **kwargs):
        context = super(PlacePortalView, self).get_context_data(*args, **kwargs)
        id_ = self.kwargs.get("id")
        place = get_object_or_404(Place, id=id_)
        # get child records from index
        q = {"query": {"parent_id": {"type": "child","id": id_ }}}
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        children = es.search(index='whg_flat', doc_type='place', body=q)['hits']
        #print('kids, type',type(children),children)
        print("id",id_)
        # build context['payload'] (parent and children if any)
        # here or in portal page?
        context['payload'] = []

        #
        # alt 1: get all from database
        ids = [id_]
        for hit in children['hits']:
            ids.append(int(hit['_id']))
        # parent and children in one queryset
        qs=Place.objects.filter(id__in=ids)
        print("ids, qs",ids,qs)
        for place in qs:        
            ds = get_object_or_404(Dataset,id=place.dataset.id)
            record = {
                "dataset":{"id":ds.id,"label":ds.label},
                "place_id":place.id,
                "src_id":place.src_id, 
                "purl":ds.uri_base+str(place.id) if 'whgaz' in ds.uri_base else ds.uri_base+place.src_id,
                "title":place.title,
                "ccodes":place.ccodes, 
                "names":[name.json for name in place.names.all()], 
                "types":[type.json for type in place.types.all()], 
                "links":[link.json for link in place.links.all()], 
                "geoms":[geom.json for geom in place.geoms.all()],
                "whens":[when.json for when in place.whens.all()], 
                "related":[rel.json for rel in place.related.all()], 
                "descriptions":[descr.json for descr in place.descriptions.all()], 
                "depictions":[depict.json for depict in place.depictions.all()]
            }
            context['payload'].append(record)
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
