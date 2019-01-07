# areas.views

from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    UpdateView,
    DeleteView )

from .forms import AreaModelForm, AreaDetailModelForm
from .models import Area

class AreaCreateView(CreateView):
    form_class = AreaModelForm
    template_name = 'areas/area_create.html'
    # template_name = 'areas/area_create_l.html'
    queryset = Area.objects.all()
    success_url = '/dashboard'

    def form_valid(self, form):
        context={}
        if form.is_valid():
            print('form is valid')
            print('cleaned_data: before ->', form.cleaned_data)
        else:
            print('form not valid', form.errors)
            context['errors'] = form.errors
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(AreaCreateView, self).get_context_data(*args, **kwargs)
        context['action'] = 'create'
        return context

# combines detail and update
class AreaDetailView(UpdateView):
    form_class = AreaDetailModelForm
    template_name = 'areas/area_detail.html'

    def get_success_url(self):
        id_ = self.kwargs.get("id")
        return '/areas/'+str(id_)+'/detail'

    def form_valid(self, form):
        context={}
        if form.is_valid():
            print('form is valid')
            print('cleaned_data: before ->', form.cleaned_data)
        else:
            print('form not valid', form.errors)
            context['errors'] = form.errors
        return super().form_valid(form)

    def get_object(self):
        print('kwargs:',self.kwargs)
        id_ = self.kwargs.get("id")
        return get_object_or_404(Area, id=id_)

    def get_context_data(self, *args, **kwargs):
        context = super(DatasetDetailView, self).get_context_data(*args, **kwargs)
        id_ = self.kwargs.get("id")

        return context

class AreaDeleteView(DeleteView):
    template_name = 'areas/area_delete.html'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Area, id=id_)

    def get_success_url(self):
        return reverse('dashboard')

# TODO: abandon for multipurpose AreaDetailView?
class AreaUpdateView(UpdateView):
    form_class = AreaModelForm
    template_name = 'areas/area_create.html'
    success_url = '/dashboard'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Area, id=id_)

    def form_valid(self, form):
        if form.is_valid():
            print(form.cleaned_data)
            obj = form.save(commit=False)
            obj.save()
        else:
            print('form not valid', form.errors)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(AreaUpdateView, self).get_context_data(*args, **kwargs)
        context['action'] = 'update'
        return context
