# datasets.views CLASS-BASED
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.forms import formset_factory, modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    CreateView,
    ListView,
    DetailView,
    UpdateView,
    DeleteView )

from .models import Dataset, Hit
from django_celery_results.models import TaskResult
from main.models import *
from .choices import AUTHORITY_BASEURI
from .forms import DatasetModelForm, HitModelForm, DatasetDetailModelForm
from .tasks import read_delimited, align_tgn, read_lpf
import codecs, tempfile, os, re, ipdb, sys, json
from pprint import pprint

def link_uri(auth,id):
    baseuri = AUTHORITY_BASEURI[auth]
    uri = baseuri + id
    return uri

def augmenter(placeid, auth, tid, hitjson):   # <- task.task_name, task.id, hits[x]['json']
    place = get_object_or_404(Place, id=placeid)
    print('augmenter params:',type(place), auth, hitjson)
    if auth == 'align_tgn':
        source = get_object_or_404(Source, src_id="getty_tgn")
        if 'location' in hitjson.keys():
            print('location:',hitjson['location'])
            geom = PlaceGeom.objects.create(
                json = hitjson['location'],
                geom_src = source,
                place_id = place,
                task_id = tid
            )
        # TODO: bulk_create??
        if len(hitjson['names']) > 0:
            for name in hitjson['names']:
                # toponym,lang,citation,when
                place_name = PlaceName.objects.create(
                    toponym = name['name'] + ('' if name['lang'] == None else '@'+name['lang']) ,
                    json = {
                        "toponym": name['name'] + ('' if name['lang'] == None else '@'+name['lang']),
                        "citation": {"id": "tgn:"+hitjson['tgnid'], "label": "Getty TGN"}
                    },
                    place_id = place,
                    task_id = tid
                )
        if hitjson['note'] != None:
            # @id,value,lang
            descrip = PlaceDescription.objects.create(
                json = {
                    "@id": 'tgn:'+hitjson['tgnid'],
                    "value": hitjson['note'],
                    "lang": "en"
                },
                place_id = place,
                task_id = tid
            )
    else:
        return

# present reconciliation hits for review, execute augmenter() for valid ones
def review(request, pk, tid): # dataset pk, celery recon task_id
    # print('pk, tid:', pk, tid)
    ds = get_object_or_404(Dataset, id=pk)
    task = get_object_or_404(TaskResult, task_id=tid)
    # TODO: also filter by reviewed, per authority

    # filter place records for those with unreviewed hits on this task
    hitplaces = Hit.objects.values('place_id').filter(task_id=tid, reviewed=False)
    record_list = Place.objects.order_by('title').filter(pk__in=hitplaces)
    # record_list = Place.objects.order_by('title').filter(dataset=ds)
    paginator = Paginator(record_list, 1)
    page = 1 if not request.GET.get('page') else request.GET.get('page')
    records = paginator.get_page(page)
    count = len(record_list)

    placeid = records[0].id
    place = get_object_or_404(Place, id=placeid)
    # print('records[0]',dir(records[0]))
    # recon task hits
    hit_list = Hit.objects.all().filter(place_id=placeid, task_id=tid)
    context = {
        'ds_id':pk, 'ds_label': ds.label, 'task_id': tid,
        'hit_list':hit_list, 'authority': task.task_name,
        'records': records,
        'page': page if request.method == 'GET' else str(int(page)-1)
    }
    # Hit model fields = ['task_id','authority','dataset','place_id',
    #     'query_pass','src_id','authrecord_id','json','geom' ]
    HitFormset = modelformset_factory(
        Hit, fields = ['id','authrecord_id','json'], form=HitModelForm, extra=0)
    formset = HitFormset(request.POST or None, queryset=hit_list)
    # formset = HitFormset(request.POST, queryset=hit_list)
    context['formset'] = formset
    print('context:',context)
    # print('formset',formset)
    method = request.method
    # required & not being sent
    # [{'task_id'(task_id), 'authority'(authority), 'dataset'(ds_label), 'place_id', 'authrecord_id', 'id'}]
    if method == 'GET':
        print('a GET')
        return render(request, 'datasets/review.html', context=context)
    else:
        print('a ',method)
        # print('formset data:',formset.data)
        if formset.is_valid():
            hits = formset.cleaned_data
            print('formset is valid, cleaned_data:',hits)
            for x in range(len(hits)):
                hit = hits[x]['id']
                if hits[x]['match'] != 'none':
                    link = PlaceLink.objects.create(
                        place_id = place,
                        task_id = tid,
                        # dataset = ds,
                        json = {
                            "type":hits[x]['match'],
                            "identifier":link_uri(task.task_name, hits[x]['authrecord_id'])
                        },
                        review_note =  hits[x]['review_note'],
                    )
                    # TODO: update <ds>.numlinked, <ds>.total_links
                    ds.numlinked = ds.numlinked +1
                    ds.total_links = ds.total_links +1
                    ds.save()
                    # TODO: add associated records as req., per hits[x]['json']
                    # task.task_name = [align_tgn|align_dbp|align_gn|align_wd]
                    augmenter(placeid, task.task_name, tid, hits[x]['json'])


                    # TODO: flag record as reviewed
                    print('place_id',placeid,
                        'authrecord_id',hits[x]['authrecord_id'],
                        'hit.id',hit.id, type(hit.id))
                # flag hit record as reviewed
                matchee = get_object_or_404(Hit, id=hit.id)
                matchee.reviewed = True
                matchee.save()
            return redirect('/datasets/'+str(pk)+'/review/'+tid+'?page='+str(int(page)))
            # return redirect('/datasets/'+str(pk)+'/review/'+tid+'?page='+str(int(page)+1))
        else:
            print('formset is NOT valid')
            print('formset data:',formset.data)
            print('errors:',formset.errors)
            # ipdb.set_trace()
            # return redirect('datasets/dashboard.html', permanent=True)
    # pprint(locals())
    return render(request, 'datasets/review.html', context=context)

# initiate, monitor align_tgn Celery task
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
        # TODO: let this vary per authority?

        # run celery/redis task
        result = align_tgn.delay(
            ds.id, ds=ds.id,
            region=request.POST['region'],
            # ccodes=request.POST['ccodes']
        )

        context['task_id'] = result.id
        context['response'] = result.state
        context['dataset id'] = ds.label
        context['authority'] = request.POST['recon']
        context['region'] = request.POST['region']
        # context['ccodes'] = request.POST['ccodes']
        # context['hits'] = '?? not wired yet'
        context['result'] = result.get()
        # context['summary'] = result.get().summary
        pprint(locals())
        return render(request, 'datasets/ds_recon.html', {'ds':ds, 'context': context})

    return render(request, 'datasets/ds_recon.html', {'ds':ds})

def task_delete(request,tid,scope='all'):
    hits = Hit.objects.all().filter(task_id=tid)
    tr = get_object_or_404(TaskResult, task_id=tid)
    ds = tr.task_args[1:-1]
    hits.delete()
    tr.delete()
    if scope == 'all':
        placelinks = PlaceLink.objects.all().filter(task_id=tid)
        placegeoms = PlaceGeom.objects.all().filter(task_id=tid)
        placenames = PlaceName.objects.all().filter(task_id=tid)
        placedescriptions = PlaceDescription.objects.all().filter(task_id=tid)
        placelinks.delete()
        placegeoms.delete()
        placenames.delete()
        placedescriptions.delete()

    # return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    # return redirect(request.get_full_path())
    return redirect('/datasets/'+ds+'/detail')

# upload file, verify format
class DatasetCreateView(CreateView):
    form_class = DatasetModelForm
    template_name = 'datasets/dataset_create.html'
    queryset = Dataset.objects.all()
    #epirus:  id	name	name_src	variants	type	aat_type	ccodes	lon	lat	min	max
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

class DashboardView(ListView):
    context_object_name = 'dataset_list'
    template_name = 'datasets/dashboard_new.html'
    # queryset = Dataset.objects.filter(owner=self.request.user).order_by('-upload_date')

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user).order_by('-upload_date')

    def get_context_data(self, *args, **kwargs):
         context = super(DashboardView, self).get_context_data(*args, **kwargs)
         # context['area_list'] = Area.objects.all().filter(owner=self.request.user)

         # TODO: user place sollections
         # context['collection_list'] = Collection.objects.all().filter(owner=self.request.user)
         print('DashboardView context:', context)
         return context

# list in dashboard
class DatasetListView(ListView):
    model = Dataset
    template_name = 'datasets/dashboard.html'
    paginate_by = 4

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user).order_by('-upload_date')

    def get_context_data(self, *args, **kwargs):
         context = super(DatasetListView, self).get_context_data(*args, **kwargs)
         context['results'] = TaskResult.objects.all()
         print('DatasetListView context:',context)
         return context

# class DatasetDetailView(DetailView):
class DatasetDetailView(UpdateView):
    form_class = DatasetDetailModelForm
    template_name = 'datasets/dataset_detail.html'

    def get_success_url(self):
        id_ = self.kwargs.get("id")
        return '/datasets/'+str(id_)+'/detail'

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
        return get_object_or_404(Dataset, id=id_)

    def get_context_data(self, *args, **kwargs):
        context = super(DatasetDetailView, self).get_context_data(*args, **kwargs)
        id_ = self.kwargs.get("id")
        ds = get_object_or_404(Dataset, id=id_)
        # print('ds',ds.label)
        placeset = Place.objects.filter(dataset=ds.label)
        context['tasks'] = TaskResult.objects.all().filter(task_args = [id_])
        print('type(tasks)',type(context['tasks']))
        # original, subject to augmentation
        context['num_links'] = PlaceLink.objects.filter(
                place_id_id__in = placeset, task_id = '').count()
        context['num_names'] = PlaceName.objects.filter(
                place_id_id__in = placeset, task_id = '').count()
        context['num_geoms'] = PlaceGeom.objects.filter(
                place_id_id__in = placeset, task_id = '').count()
        context['num_descriptions'] = PlaceDescription.objects.filter(
                place_id_id__in = placeset, task_id = '').count()
        # others
        context['num_types'] = PlaceType.objects.filter(
                place_id_id__in = placeset).count()
        context['num_when'] = PlaceWhen.objects.filter(
                place_id_id__in = placeset).count()
        context['num_related'] = PlaceRelated.objects.filter(
                place_id_id__in = placeset).count()
        context['num_depictions'] = PlaceDepiction.objects.filter(
                place_id_id__in = placeset).count()

        # augmentations (has task_id)
        context['links_added'] = PlaceLink.objects.filter(
                place_id_id__in = placeset, task_id__contains = '-').count()
        context['names_added'] = PlaceName.objects.filter(
                place_id_id__in = placeset, task_id__contains = '-').count()
        context['geoms_added'] = PlaceGeom.objects.filter(
                place_id_id__in = placeset, task_id__contains = '-').count()
        context['descriptions_added'] = PlaceDescription.objects.filter(
                place_id_id__in = placeset, task_id__contains = '-').count()

        return context

# "edit metadata"
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
    place_list = Place.objects.filter(dataset=label).order_by('id')

    return render(request, 'datasets/ds_grid.html', {'ds':ds, 'place_list': place_list})

# insert LP-compatible records from csv file to database
def ds_insert(request, pk ):
    # retrieve just-added file, insert to db
    import os, csv, codecs,json
    dataset = get_object_or_404(Dataset, id=pk)
    context = {'status': 'inserting'} #??

    infile = dataset.file.open(mode="r")
    # should already know delimiter
    dialect = csv.Sniffer().sniff(infile.read(16000),['\t',';','|'])
    reader = csv.reader(infile, dialect)
    infile.seek(0)
    header = next(reader, None)
    print('header', header)

    objs = {"PlaceName":[], "PlaceType":[], "PlaceGeom":[], "PlaceWhen":[],
        "PlaceLink":[], "PlaceRelated":[], "PlaceDescription":[],
        "PlaceDepiction":[]}

    # CSV * = req; ^ = desired
    # id*, name*, name_src*, type^, variants[], parent^, ccodes[]^, lon^, lat^,
    # geom_src, close_match[]^, exact_match[]^, description, depiction

    # TODO: what if simultaneous inserts?
    countrows=0
    countlinked = 0
    countlinks = 0
    # for r in reader:
    for i, r in zip(range(200), reader):
        # TODO: should columns be required even if blank?
        # required
        src_id = r[header.index('id')]
        title = r[header.index('title')]
        # for PlaceName insertion, strip anything in parens
        name = re.sub(' \(.*?\)', '', title)
        name_src = r[header.index('name_src')]
        variants = r[header.index('variants')].split(', ') if 'variants' in header else []
        # encouraged for reconciliation
        type = r[header.index('type')] if 'type' in header else 'not specified'
        aat_type = r[header.index('aat_type')] if 'aat_type' in header else ''
        parent = r[header.index('parent')] if 'parent' in header else ''
        # ccodes = r[header.index('ccodes')][2:-2].split('", "') \
        ccodes = r[header.index('ccodes')][2:-2].split('","') \
            if 'ccodes' in header else []
        coords = [
            float(r[header.index('lon')]),
            float(r[header.index('lat')]) ] if 'lon' in header else []
        close_match = r[header.index('close_match')][1:-1].split('", "') \
            if 'close_match' in header else []
        exact_match = r[header.index('exact_match')][1:-1].split('", "') \
            if 'exact_match' in header else []
        # nice to have
        minmax = [
            r[header.index('min')],
            r[header.index('max')] ] if 'min' in header else []
        description = r[header.index('description')] \
            if 'description' in header else []
        depiction = r[header.index('depiction')] \
            if 'depiction' in header else []

        print('variants:',variants)
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
            toponym = name,
            # TODO get citation label through name_src FK; here?
            json={"toponym": name, "citation": {"id":name_src,"label":""}}
        ))

        # variants if any
        if len(variants) > 0:
            for v in variants:
                objs['PlaceName'].append(PlaceName(place_id=newpl,
                    toponym = v,
                    json={"toponym": v, "citation": {"id":name_src,"label":""}}
                ))

        # PlaceType()
        objs['PlaceType'].append(PlaceType(place_id=newpl,
            json={"src_label": type, "label":aat_type}
        ))

        # PlaceGeom()
        # TODO: test geometry type or force geojson
        if 'lon' in header and (coords[0] != 0 and coords[1] != 0):
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

        # PlaceRelated()
        if 'parent' in header:
            objs['PlaceRelated'].append(PlaceRelated(place_id=newpl,
                json={
                    "relation_type": "gvp:broaderPartitive",
                    "relation_to": "",
                    "label": parent
                }
            ))

        # PlaceWhen()
        # timespans[{start{}, end{}}], periods[{name,id}], label, duration
        if 'min' in header:
            objs['PlaceWhen'].append(PlaceWhen(place_id=newpl,
                json={
                    "timespans": [{"start":{"earliest":minmax[0]}, "end":{"latest":minmax[1]}}]
                }
            ))

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
    PlaceWhen.objects.bulk_create(objs['PlaceWhen'])
    PlaceLink.objects.bulk_create(objs['PlaceLink'])
    PlaceRelated.objects.bulk_create(objs['PlaceRelated'])

    context['status'] = 'in_database'
    print('rows,linked,links:',countrows,countlinked,countlinks)
    dataset.numrows = countrows
    dataset.numlinked = countlinked
    dataset.total_links = countlinks
    dataset.header = header
    dataset.status = 'in_database'
    dataset.save()
    print('record:', dataset.__dict__)
    print('context:',context)
    infile.close()
    # dataset.file.close()

    return redirect('/dashboard', context=context)
