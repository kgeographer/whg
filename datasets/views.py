# datasets.views
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.forms import formset_factory, modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import (
    CreateView, ListView, UpdateView, DeleteView, DetailView )

import codecs, tempfile, os, re, ipdb, sys
import simplejson as json
from pprint import pprint
from django_celery_results.models import TaskResult
from .models import Dataset, Hit
from areas.models import Area
from places.models import *
from main.choices import AUTHORITY_BASEURI
from .forms import DatasetModelForm, HitModelForm, DatasetDetailModelForm
from .tasks import read_delimited, align_tgn, read_lpf
from .utils import parsejson, myteam, parse_wkt

def link_uri(auth,id):
    baseuri = AUTHORITY_BASEURI[auth]
    uri = baseuri + id
    return uri

# create place_name, place_geom, place_description records as req.
def augmenter(placeid, auth, tid, hitjson):
    place = get_object_or_404(Place, id=placeid)
    task = get_object_or_404(TaskResult, task_id=tid)
    kwargs=json.loads(task.task_kwargs.replace("\'", "\""))
    print('augmenter params:',type(place), auth, hitjson)
    if auth == 'align_tgn':
        source = get_object_or_404(Source, src_id="getty_tgn")
        # don't add place_geom record unless flagged in task
        if 'location' in hitjson.keys() and kwargs['aug_geom'] == 'on':
            geojson=hitjson['location']
            # add geowkt and citation{id,label}
            geojson['geowkt']='POINT('+str(geojson['coordinates'][0])+' '+str(geojson['coordinates'][0])+')'
            geojson['citation']={
                "id": "tgn:"+hitjson['tgnid'],
                "label":"Getty TGN"
            }
            geom = PlaceGeom.objects.create(
                json = geojson,
                # json = hitjson['location'],
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
                    # update <ds>.numlinked, <ds>.total_links
                    ds.numlinked = ds.numlinked +1
                    ds.total_links = ds.total_links +1
                    ds.save()
                    # TODO: augment fields for match 
                    # task.task_name = [align_tgn|align_dbp|align_gn|align_wd]
                    # ignore TGN geometry for non-point physical geography datasets
                    #hits[x]['json']['geom'] = True if ds in ('ne_rivers','ne_mountains','wri_lakes') else False
                    #hits[x]['json']['geom'] = True if task.task_kwargs['aug_geom'] == 'on' else False
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
    # TODO: handle multipolygons from "#area_load" and "#area_draw"
    # depends on making es:tgn locations geo_shapes
    area_list = Area.objects.all().filter(owner=request.user, type="#areas_codes")
    # area_list = Area.objects.all().filter(owner=request.user)
    # print('request, method:',request, request.method)
    context = {
        "dataset": ds.name,
        "area_list": area_list
    }

    if request.method == 'GET':
        print('request:',request)
    elif request.method == 'POST' and request.POST:
        fun = eval('align_'+request.POST['recon'])
        # TODO: let this vary per authority?
        region = request.POST['region'] # pre-defined UN regions
        userarea = request.POST['userarea'] #
        aug_names = request.POST['aug_names'] #
        aug_notes = request.POST['aug_notes'] #
        aug_geom = request.POST['aug_geom'] #
        bounds={
            "type":["region" if region !="0" else "userarea"],
            "id": [region if region !="0" else userarea]
        }
        print('bounds',bounds)
        # run celery/redis task
        result = align_tgn.delay(
            ds.id,
            ds=ds.id,
            dslabel=ds.label,
            owner=ds.owner.id,
            bounds=bounds,
            aug_names=aug_names,
            aug_notes=aug_notes,
            aug_geom=aug_geom
        )

        context['task_id'] = result.id
        context['response'] = result.state
        context['dataset id'] = ds.label
        context['authority'] = request.POST['recon']
        context['region'] = request.POST['region']
        context['userarea'] = request.POST['userarea']
        context['aug_names'] = request.POST['aug_names']
        context['aug_notes'] = request.POST['aug_notes']
        context['aug_geom'] = request.POST['aug_geom']
        # context['ccodes'] = request.POST['ccodes']
        # context['hits'] = '?? not wired yet'
        context['result'] = result.get()
        # context['summary'] = result.get().summary
        pprint(locals())
        return render(request, 'datasets/ds_recon.html', {'ds':ds, 'context': context})

    return render(request, 'datasets/ds_recon.html', {'ds':ds, 'area_list':area_list})

def task_delete(request,tid, scope='task'):
    hits = Hit.objects.all().filter(task_id=tid)
    tr = get_object_or_404(TaskResult, task_id=tid)
    ds = tr.task_args[1:-1]
    if scope == 'task':
        hits.delete()
        tr.delete()
    if scope in ['matches']:
        for h in hits:
            h.reviewed = False
            h.save()
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


# simple table for viewing datasets
def ds_grid(request, label):
    print('request, pk',request, label)
    ds = get_object_or_404(Dataset, label=label)
    place_list = Place.objects.filter(dataset=label).order_by('title')

    return render(request, 'datasets/ds_grid.html', {'ds':ds, 'place_list': place_list})


# better table for viewing datasets
def drf_table(request, label, f):
    # need only for title; calls API w/javascript for data
    ds = get_object_or_404(Dataset, label=label)
    filt = f
    return render(request, 'datasets/drf_table.html', {'ds':ds,'filter':filt})

# insert LP-csv file to database
# TODO: require, handle sources
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
    # lists are ';' delimited, no brackets
    # id*, title*, name_src*, type^, variants[], parent^, ccodes[]^, lon^, lat^,
    # geom_src, close_match[]^, exact_match[]^, description, depiction

    # TODO: what if simultaneous inserts?
    countrows=0
    countlinked = 0
    countlinks = 0
    #for r in reader:
    for i, r in zip(range(100), reader):
        # TODO: should columns be required even if blank?
        # required
        src_id = r[header.index('id')]
        title = r[header.index('title')]
        # for PlaceName insertion, strip anything in parens
        name = re.sub(' \(.*?\)', '', title)
        name_src = r[header.index('name_src')]
        if 'variants' in header:
            v = r[header.index('variants')].split(';') 
            variants = v if '' not in v else []
        else:
            variants = []
        # encouraged for reconciliation
        type = r[header.index('type')] if 'type' in header else 'not specified'
        aat_type = r[header.index('aat_type')] if 'aat_type' in header else ''
        parent = r[header.index('parent')] if 'parent' in header else ''
        #standardize on ';' for name and ccode arrays in tab-delimited files
        #ccodes = r[header.index('ccodes')][2:-2].split(', ') \
        ccodes = r[header.index('ccodes')].split(';') \
            if 'ccodes' in header else []
        coords = [
            float(r[header.index('lon')]),
            float(r[header.index('lat')]) ] if 'lon' in header else []
        close_match = r[header.index('close_match')].split(';') \
            if 'close_match' in header else []
        exact_match = r[header.index('exact_match')].split(';') \
            if 'exact_match' in header else []
        # nice to have
        minmax = [
            r[header.index('min')],
            r[header.index('max')] ] if 'min' in header else []
        description = r[header.index('description')] \
            if 'description' in header else []
        depiction = r[header.index('depiction')] \
            if 'depiction' in header else []

        #print('variants:',variants)
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
                json={"type": "Point", "coordinates": coords,
                    "geowkt": 'POINT('+str(coords[0])+' '+str(coords[1])+')'}
            ))
        elif 'geowkt' in header:
            objs['PlaceGeom'].append(PlaceGeom(place_id=newpl,
                json=parse_wkt(r[header.index('geowkt')])
            ))            
            
        # PlaceLink() - close
        if len(list(filter(None,close_match))) > 0:
            countlinked += 1
            for m in close_match:
                countlinks += 1
                objs['PlaceLink'].append(PlaceLink(place_id=newpl,
                    json={"type":"closeMatch", "identifier":m}
                ))

        # PlaceLink() - exact
        if len(list(filter(None,exact_match))) > 0:
            countlinked += 1
            for m in exact_match:
                countlinks += 1
                objs['PlaceLink'].append(PlaceLink(place_id=newpl,
                    json={"type":"exactMatch", "identifier":m}
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


# list user datasets, area, place collections
class DashboardView(ListView):
    context_object_name = 'dataset_list'
    template_name = 'datasets/dashboard.html'

    def get_queryset(self):
        # TODO: make .team() a method on User
        me = self.request.user
        if me.username == 'whgadmin':
            return Dataset.objects.all().order_by('id')
        else:
            return Dataset.objects.filter(owner__in=myteam(me)).order_by('id')
        

    def get_context_data(self, *args, **kwargs):
        teamtasks=[]
        me = self.request.user
        context = super(DashboardView, self).get_context_data(*args, **kwargs)

        # list areas
        if me.username == 'whgadmin':
            context['area_list'] = Area.objects.all().order_by('-created')
        else:
            context['area_list'] = Area.objects.all().filter(owner=self.request.user).order_by('-created')

        # list team tasks
        if me.username == 'whgadmin':
            context['review_list'] = TaskResult.objects.filter(status='SUCCESS').order_by('-date_done')
        else:
            for t in TaskResult.objects.filter(status='SUCCESS'):
                tj=json.loads(t.task_kwargs.replace("\'", "\""))
                u=get_object_or_404(User,id=tj['owner'])
                print('args,task owner',tj,u)
                if u in myteam(me):
                    teamtasks.append(t.task_id)
            context['review_list'] = TaskResult.objects.filter(task_id__in=teamtasks).order_by('-date_done')

        # TODO: user place collections
        print('DashboardView context:', context)
        return context


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


# detail
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
        context['status'] = ds.status
        placeset = Place.objects.filter(dataset=ds.label)
        context['tasks'] = TaskResult.objects.all().filter(task_args = [id_],status='SUCCESS')
        # context['tasks'] = TaskResult.objects.all().filter(task_args = [id_])
        print('type(tasks)',type(context['tasks']))
        # initial (non-task)
        context['num_links'] = PlaceLink.objects.filter(
                place_id_id__in = placeset, task_id = None).count()
        context['num_names'] = PlaceName.objects.filter(
                place_id_id__in = placeset, task_id = None).count()
        context['num_geoms'] = PlaceGeom.objects.filter(
                place_id_id__in = placeset, task_id = None).count()
        context['num_descriptions'] = PlaceDescription.objects.filter(
                place_id_id__in = placeset, task_id = None).count()
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


# confirm ok on delete
class DatasetDeleteView(DeleteView):
    template_name = 'datasets/dataset_delete.html'

    def get_object(self):
        id_ = self.kwargs.get("id")
        return get_object_or_404(Dataset, id=id_)

    def get_success_url(self):
        return reverse('dashboard')
