# api.views

from django.contrib.auth.models import User, Group
from rest_framework import generics
from rest_framework import permissions
from rest_framework import viewsets

from .serializers import UserSerializer, GroupSerializer, DatasetSerializer, \
    PlaceSerializer

from api.permissions import IsOwnerOrReadOnly
from datasets.models import Dataset
from main.models import Place #, PlaceName, PlaceType

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().order_by('label')
    serializer_class = DatasetSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)


class PlaceViewSet(viewsets.ModelViewSet):
    queryset = Place.objects.all().order_by('title')
    serializer_class = PlaceSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)

    def get_queryset(self):
        qs = Place.objects.all()
        query = self. request.GET.get('q')
        if query is not None:
            # qs = qs.filter(title__istartswith=query)
            qs = qs.filter(title__icontains=query)
        return qs


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
