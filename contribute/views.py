# contribute.views
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from pprint import pprint
import django.core.files.uploadedfile as upfile
import codecs, tempfile, os

from .tasks import read_csv, read_lpf
from .forms import DatasetModelForm
from .models import Dataset

def home(request):
    return render(request, 'contribute/home.html')

# list datasets per user
def dashboard(request):
    dataset_list = Dataset.objects.filter(owner=request.user.id).order_by('-upload_date')
    print('dataset_list',dataset_list)
    return render(request, 'contribute/dashboard.html', {'datasets':dataset_list})

# new dataset: upload file, store if valid
def ds_new(request, template_name='contribute/ds_form.html'):
    form = DatasetModelForm(request.POST, request.FILES)
    context = {
        'form':form, 'action': 'new'
    }
    def removekey(d, key):
        r = dict(d)
        del r[key]
        return r

    if request.method == 'POST':
        if form.is_valid():
            context['action'] = 'upload'
            print('form is valid')
            print('cleaned_data', form.cleaned_data)

            # open & write tempf to a temp location;
            # call it tempfn for reference
            tempf, tempfn = tempfile.mkstemp()
            try:
                for chunk in request.FILES['file'].chunks():
                    os.write(tempf, chunk)
            except:
                raise Exception("Problem with the input file %s" % request.FILES['file'])
            finally:
                os.close(tempf)

            # open temp file
            fin = codecs.open(tempfn, 'r', 'utf8')
            # send for format validation
            if form.cleaned_data['format'] == 'csv':
                result = read_csv(fin,request.user.username)
            elif form.cleaned_data['format'] == 'lpf':
                result = read_lpf(fin,request.user.username)
            # print('cleaned_data',form.cleaned_data)
            fin.close()

            # add status
            if len(result['errors']) == 0:
                context['status'] = 'format_ok'
                form.save()
            else:
                context['status'] = 'format_error'
                print('result:', result)

            context['result'] = result
            # return redirect('/contribute/dashboard')
        else:
            print('not valid', form.errors)
            context['errors'] = form.errors
        print('context',context)
    return render(request, template_name, context=context)

def ds_insert(request, pk ):
    # retrieve just-added record then db insert
    record = get_object_or_404(Dataset, label=label)
    # form = DatasetModelForm(request.POST or None, instance=record)
    print('record', record)
    context = {'status': 'inserted'}
    # if form.is_valid():
    #     # open & write tempf to a temp location;
    #     # call it tempfn for reference
    #     tempf, tempfn = tempfile.mkstemp()
    #     try:
    #         for chunk in request.FILES['file'].chunks():
    #             os.write(tempf, chunk)
    #     except:
    #         raise Exception("Problem with the input file %s" % request.FILES['file'])
    #     finally:
    #         os.close(tempf)
    #
    #     # open temp file
    #     fin = codecs.open(tempfn, 'r', 'utf8')
    #     # send for format validation
    #     if form.cleaned_data['format'] == 'csv':
    #         reader = csv.reader(fin)
    #         count = sum(1 for row in reader)
    #         print('count:',count)
    #         # result = read_csv(fin)
    #     elif form.cleaned_data['format'] == 'lpf':
    #         result = read_lpf(fin)
    #     # print('cleaned_data',form.cleaned_data)
    #     fin.close()
    #
    #     # form.save()
    return redirect('/contribute/dashboard', context=context)
    # else:
    #     pprint(locals())
    #     print('not valid', form.errors)
    # return render(request, template_name, {'form':form, 'action': 'insert'})

def ds_update(request, pk, template_name='contribute/ds_form.html'):
    record = get_object_or_404(Dataset, pk=pk)
    form = DatasetModelForm(request.POST or None, instance=record)
    if form.is_valid():
        form.save()
        return redirect('/contribute/dashboard')
    return render(request, template_name, {'form':form, 'action': 'update'})

def ds_delete(request, pk):
    record = get_object_or_404(Dataset, pk=pk)
    # it's a GET not POST
    record.delete()
    return redirect('contrib_dashboard')
