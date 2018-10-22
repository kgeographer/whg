# contribute.views
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from main.models import Dataset
from .forms import DatasetModelForm
from pprint import pprint
import django.core.files.uploadedfile as upfile
import codecs, tempfile, os
from .tasks import validate

def home(request):
    return render(request, 'contribute/home.html')

# list datasets per user
def dashboard(request):
    dataset_list = Dataset.objects.filter(user=request.user.id).order_by('-uploaded')
    print('dataset_list',dataset_list)
    return render(request, 'contribute/dashboard.html', {'datasets':dataset_list})

# new dataset: upload file, store if valid
def ds_new(request, template_name='contribute/ds_form.html'):
    form = DatasetModelForm(request.POST, request.FILES)
    context = {
        'form':form, 'action': 'new'
    }
    if form.is_valid():
        print('form is valid')
        # validate the file
        filey = request.FILES['file'].file

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

        # open and analyze it, gathering errors
        errors = []
        fin = codecs.open(tempfn, 'r', 'utf8')
        rows = fin.readlines()[:10]
        fin.close()
        # TODO: validate logic here
        # header = rows[0][:-1].split(',')
        # for x in range(len(rows[1:])):
        #     row_list = rows[x].split(',')
        #     # check list length
        #
        #     # test error output
        #     errors.append({'id':x, 'boogered': row_list[3]})
        pprint(errors)

        context['errors'] = errors
        
        # if validated, save to user folder and return
        form.save()
        return redirect('/contribute/dashboard')
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
