# datasets.views CLASS-BASED

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    UpdateView,
    DeleteView )

from .models import Dataset
from main.models import *
from .forms import DatasetModelForm
from .tasks import read_delimited, align_tgn, read_lpf, add, mul, xsum
import codecs, tempfile, os
from pprint import pprint

# initiate, monitor reconciliation service
def ds_recon(request, pk):
    ds = get_object_or_404(Dataset, id=pk)
    # print('request, method:',request, request.method)
    context = {
        "dataset": ds.name,
    }
    if request.method == 'GET':
        print('request:',request)
    elif request.method == 'POST' and request.POST:
        fun = eval('align_'+request.POST['recon'])
        # pprint(request.POST)

        # run celery/redis task
        # result = fun.delay(ds)
        result = align_tgn.delay(ds.id)

        context['task_id'] = result.id
        context['response'] = result.state
        context['dataset id'] = ds.label
        context['authority'] = request.POST['recon']
        context['hits'] = '?? not wired yet'
        context['result'] = result.get()
        # pprint(locals())
        return render(request, 'datasets/ds_recon.html', {'ds':ds, 'context': context})

    return render(request, 'datasets/ds_recon.html', {'ds':ds})

# distinct from (redundant to?) api.views
class DatasetCreateView(CreateView):
    form_class = DatasetModelForm
    template_name = 'datasets/dataset_create.html'
    queryset = Dataset.objects.all()

    def form_valid(self, form):
        context={}
        if form.is_valid():
            print('form is valid')
            print('cleaned_data: before ->', form.cleaned_data)

            # open & write tempf to a temp location;
            # call it tempfn for reference
            tempf, tempfn = tempfile.mkstemp()
            try:
                for chunk in form.cleaned_data['file'].chunks():
                # for chunk in request.FILES['file'].chunks():
                    os.write(tempf, chunk)
            except:
                raise Exception("Problem with the input file %s" % request.FILES['file'])
            finally:
                os.close(tempf)

            # open the temp file
            fin = codecs.open(tempfn, 'r', 'utf8')
            # send for format validation
            if form.cleaned_data['format'] == 'delimited':
                result = read_delimited(fin,form.cleaned_data['owner'])
                # result = read_csv(fin,request.user.username)
            elif form.cleaned_data['format'] == 'lpf':
                result = read_lpf(fin,form.cleaned_data['owner'])
                # result = read_lpf(fin,request.user.username)
            # print('cleaned_data',form.cleaned_data)
            fin.close()

            # add status & stats
            if len(result['errors'].keys()) == 0:
                print('columns, type', result['columns'], type(result['columns']))
                obj = form.save(commit=False)
                obj.status = 'format_ok'
                # form.format = result['format']
                obj.format = result['format']
                obj.delimiter = result['delimiter']
                # # form.cleaned_data['delimiter'] = result['delimiter']
                obj.numrows = result['count']
                obj.header = result['columns']
                print('cleaned_data:after ->',form.cleaned_data)
                obj.save()
            else:
                context['status'] = 'format_error'
                print('result:', result)

        else:
            print('form not valid', form.errors)
            context['errors'] = form.errors
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(DatasetCreateView, self).get_context_data(*args, **kwargs)
        context['action'] = 'create'
        return context

class DatasetListView(ListView):
    model = Dataset
    template_name = 'datasets/dashboard.html'
    paginate_by = 4

    def get_queryset(self):
        return Dataset.objects.filter(owner = self.request.user)

class DatasetDetailView(DetailView):
    template_name = 'datasets/dataset_detail.html'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Dataset, id=id_)

class DatasetUpdateView(UpdateView):
    form_class = DatasetModelForm
    template_name = 'datasets/dataset_create.html'
    success_url = '/dashboard'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Dataset, id=id_)

    def form_valid(self, form):
        if form.is_valid():
            print(form.cleaned_data)
        else:
            print('form not valid', form.errors)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(DatasetUpdateView, self).get_context_data(*args, **kwargs)
        context['action'] = 'update'
        return context

class DatasetDeleteView(DeleteView):
    template_name = 'datasets/dataset_delete.html'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Dataset, id=id_)

    def get_success_url(self):
        return reverse('dashboard')

def ds_grid(request, label):
    print('request, pk',request, label)
    ds = get_object_or_404(Dataset, label=label)
    place_list = Place.objects.filter(dataset=label).order_by('title')

    return render(request, 'datasets/ds_grid.html', {'ds':ds, 'place_list': place_list})

# insert LP-compatible records from csv file to database
def ds_insert(request, pk ):
    # retrieve just-added record then db insert
    import os, csv, codecs,json
    dataset = get_object_or_404(Dataset, id=pk)
    context = {'status': 'inserting'}

    infile = dataset.file.open(mode="r")
    # already know delimiter
    dialect = csv.Sniffer().sniff(infile.read(16000),['\t',';','|'])
    reader = csv.reader(infile, dialect)
    infile.seek(0)
    header = next(reader, None)
    print('header', header)

    objs = {"PlaceName":[], "PlaceType":[], "PlaceGeom":[], "PlaceWhen":[],
        "PlaceLink":[], "PlaceRelated":[], "PlaceDescription":[],
        "PlaceDepiction":[]}

    # id*, name*, name_src*, type^, variants[], ccodes[]^, lon^, lat^, geom_src, close_match[]^, exact_match[]^, description, depiction
    #
    # TODO: what if simultaneous inserts?
    countrows=0
    countlinked = 0
    countlinks = 0
    # for r in reader:
    for i, r in zip(range(200), reader):
        # ABANDONED place.placeid ## poll Place.objects.placeid.max()
        # nextpid = (Place.objects.all().aggregate(models.Max('id'))['id__max'] or 0) + 1
            # if Place.objects.all().count() > 0 else 10000001

        # TODO: should columns be required even if blank?
        # required
        src_id = r[header.index('id')]
        title = r[header.index('name')]
        name_src = r[header.index('name_src')]
        # encouraged for reconciliation
        type = r[header.index('type')] if 'type' in header else 'unk.'
        aat_type = r[header.index('aat_type')] if 'aat_type' in header else ''
        ccodes = r[header.index('ccodes')][2:-2].split('", "') if 'ccodes' in header else []
        coords = [float(r[header.index('lon')]), float(r[header.index('lat')])]
        close_match = r[header.index('close_match')][2:-2].split('", "') if 'close_match' in header else []
        exact_match = r[header.index('exact_match')][1:-1] \
            if 'exact_match' in header else []
        # nice to have
        description = r[header.index('description')] \
            if 'description' in header else []
        depiction = r[header.index('depiction')] \
            if 'depiction' in header else []

        # build and save Place object
        newpl = Place(
            # placeid = nextpid,
            src_id = src_id,
            dataset = dataset,
            title = title,
            ccodes = ccodes
        )
        newpl.save()
        countrows += 1
        # build associated objects and add to arrays

        # PlaceName()
        objs['PlaceName'].append(PlaceName(place_id=newpl,
            # src_id = src_id,
            # dataset = dataset,
            toponym = title,
            # TODO get citation label through name_src FK; here?
            json={"toponym": title, "citation": {"id":name_src,"label":""}}
        ))
        # TODO: variants array

        # PlaceType()
        objs['PlaceType'].append(PlaceType(place_id=newpl,
            json={"src_label": type, "label":aat_type}
        ))

        # PlaceGeom()
        objs['PlaceGeom'].append(PlaceGeom(place_id=newpl,
            # src_id = src_id,
            # dataset = dataset,
            json={"type": "Point", "coordinates": coords,
                "geowkt": 'POINT('+str(coords[0])+' '+str(coords[1])+')'}
        ))

        # # PlaceLink()
        if len(list(filter(None,close_match))) > 0:
            countlinked += 1
            # print('close_match',close_match)
            for m in close_match:
                countlinks += 1
                objs['PlaceLink'].append(PlaceLink(place_id=newpl,
                    # src_id = src_id,
                    # dataset = dataset,
                    json={"type":"closeMatch", "identifier":m}
                ))

        #
        # # PlaceWhen()
        # objs['PlaceWhen'].append(PlaceWhen())
        #
        # # PlaceRelated()
        # objs['PlaceRelated'].append(PlaceRelated())
        #
        # # PlaceDescription()
        # objs['PlaceDescription'].append(PlaceDescription())
        #
        # # PlaceDepiction()
        # objs['PlaceDepiction'].append(PlaceDepiction())

        # print('new place:', newpl)

    # bulk_create(Class, batchsize=n) for each
    PlaceName.objects.bulk_create(objs['PlaceName'])
    PlaceType.objects.bulk_create(objs['PlaceType'])
    PlaceGeom.objects.bulk_create(objs['PlaceGeom'])
    PlaceLink.objects.bulk_create(objs['PlaceLink'])

    context['status'] = 'inserted'
    print('rows,linked,links:',countrows,countlinked,countlinks)
    dataset.numrows = countrows
    dataset.numlinked = countlinked
    dataset.total_links = countlinks
    # dataset.header = header
    dataset.status = 'inserted'
    dataset.save()
    print('record:', dataset.__dict__)
    print('context:',context)
    infile.close()
    # dataset.file.close()

    return redirect('/dashboard', context=context)

##
# outdated FBVs
##
# def dashboard(request):
#     dataset_list = Dataset.objects.filter(owner=request.user.id).order_by('-upload_date')
#     print('dataset_list',dataset_list)
#     return render(request, 'datasets/dashboard.html', {'datasets':dataset_list})
#
# # new dataset: upload file, store if valid
# def ds_new(request, template_name='datasets/ds_form.html'):
#     form = DatasetModelForm(request.POST, request.FILES)
#     context = {
#         'form':form, 'action': 'new'
#     }
#     def removekey(d, key):
#         r = dict(d)
#         del r[key]
#         return r
#
#     if request.method == 'POST':
#         if form.is_valid():
#             context['action'] = 'upload'
#             print('form is valid')
#             print('cleaned_data', form.cleaned_data)
#
#             # open & write tempf to a temp location;
#             # call it tempfn for reference
#             tempf, tempfn = tempfile.mkstemp()
#             try:
#                 for chunk in request.FILES['file'].chunks():
#                     os.write(tempf, chunk)
#             except:
#                 raise Exception("Problem with the input file %s" % request.FILES['file'])
#             finally:
#                 os.close(tempf)
#
#             # open temp file
#             fin = codecs.open(tempfn, 'r', 'utf8')
#             # send for format validation
#             if form.cleaned_data['format'] == 'csv':
#                 result = read_csv(fin,request.user.username)
#             elif form.cleaned_data['format'] == 'lpf':
#                 result = read_lpf(fin,request.user.username)
#             # print('cleaned_data',form.cleaned_data)
#             fin.close()
#
#             # add status
#             if len(result['errors']) == 0:
#                 context['status'] = 'format_ok'
#                 form.cleaned_data['status'] = 'format_ok'
#                 form.save()
#             else:
#                 context['status'] = 'format_error'
#                 print('result:', result)
#
#             context['result'] = result
#             # return redirect('/datasets/dashboard')
#         else:
#             print('not valid', form.errors)
#             context['errors'] = form.errors
#         print('context',context)
#     return render(request, template_name, context=context)
#
# def ds_update(request, pk, template_name='datasets/ds_form.html'):
#     record = get_object_or_404(Dataset, pk=pk)
#     form = DatasetModelForm(request.POST or None, instance=record)
#     if form.is_valid():
#         form.save()
#         return redirect('/datasets/dashboard')
#     else:
#         print('not valid', form.errors)
#     return render(request, template_name, {'form':form, 'action': 'update'})
#
# def ds_delete(request, pk):
#     record = get_object_or_404(Dataset, pk=pk)
#     # print('request, pk',request, pk)
#     # print('record',type(record))
#     # it's a GET not POST
#     record.delete()
#     return redirect('dashboard')
