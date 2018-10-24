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
    if form.is_valid():
        print('form is valid')

        # data file already validated?
        if form.cleaned_data['status'] == 'format_ok':
            form.save()
            # TODO: save to database
            return redirect('/contribute/dashboard')

        # get the file object
        # filey = request.FILES['file'].file

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
            result = read_csv(fin)
        elif form.cleaned_data['format'] == 'lpf':
            result = read_lpf(fin)
        print('cleaned_data',form.cleaned_data)
        fin.close()

        # add status
        if len(result['errors']) == 0:
            context['status'] = 'format_ok'
            print('result:', removekey(result, 'geom'))
        else:
            context['status'] = 'format_error'
            print('result:', result)

        context['result'] = removekey(result, 'geom')
        # return redirect('/contribute/dashboard')
    else:
        pprint(form.errors)
    return render(request, template_name, context=context)

def ds_update(request, pk, template_name='contribute/ds_form.html'):
    dataset = get_object_or_404(Dataset, pk=pk)
    form = DatasetModelForm(request.POST or None, instance=dataset)
    if form.is_valid():
        form.save()
        return redirect('/contribute/dashboard')
    return render(request, template_name, {'form':form, 'action': 'update'})

def ds_delete(request, pk):
    dataset= get_object_or_404(Dataset, pk=pk)
    # it's a GET not POST
    dataset.delete()
    return redirect('contrib_dashboard')
