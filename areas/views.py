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
    queryset = Area.objects.all()

    def form_valid(self, form):
        context={}
        if form.is_valid():
            print('form is valid')
            print('cleaned_data: before ->', form.cleaned_data)

            # # open & write tempf to a temp location;
            # # call it tempfn for reference
            # tempf, tempfn = tempfile.mkstemp()
            # try:
            #     for chunk in form.cleaned_data['file'].chunks():
            #         os.write(tempf, chunk)
            # except:
            #     raise Exception("Problem with the input file %s" % request.FILES['file'])
            # finally:
            #     os.close(tempf)
            #
            # # open the temp file
            # fin = codecs.open(tempfn, 'r', 'utf8')
            # # send for format validation
            # if form.cleaned_data['format'] == 'delimited':
            #     result = read_delimited(fin,form.cleaned_data['owner'])
            #     # result = read_csv(fin,request.user.username)
            # elif form.cleaned_data['format'] == 'lpf':
            #     result = read_lpf(fin,form.cleaned_data['owner'])
            #     # result = read_lpf(fin,request.user.username)
            # # print('cleaned_data',form.cleaned_data)
            # fin.close()
            #
            # # add status & stats
            # if len(result['errors'].keys()) == 0:
            #     print('columns, type', result['columns'], type(result['columns']))
            #     obj = form.save(commit=False)
            #     obj.status = 'format_ok'
            #     # form.format = result['format']
            #     obj.format = result['format']
            #     obj.delimiter = result['delimiter']
            #     # # form.cleaned_data['delimiter'] = result['delimiter']
            #     obj.numrows = result['count']
            #     obj.header = result['columns']
            #     print('cleaned_data:after ->',form.cleaned_data)
            #     obj.save()
            # else:
            #     context['status'] = 'format_error'
            #     print('result:', result)
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
