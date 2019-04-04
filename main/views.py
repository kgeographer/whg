# main.views

from django.shortcuts import render
from django.urls import reverse_lazy
from .forms import CommentModalForm
from areas.models import Area
from bootstrap_modal_forms.generic import BSModalCreateView

class CommentCreateView(BSModalCreateView):
    template_name = 'main/create_comment.html'
    form_class = CommentModalForm
    success_message = 'Success: Comment (Area for now) was created.'
    success_url = reverse_lazy('index')