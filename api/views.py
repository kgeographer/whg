# api.views

from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import generics
from .serializers import UserSerializer, GroupSerializer, DatasetSerializer, \
    PlaceSerializer, PlaceNameSerializer, PlaceTypeSerializer

from contribute.models import Dataset
from main.models import Place, PlaceName, PlaceType

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().order_by('label')
    serializer_class = DatasetSerializer

class PlaceViewSet(viewsets.ModelViewSet):
# class PlaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Place.objects.all().order_by('title')
    serializer_class = PlaceSerializer

# TODO: get place url to use placeid, not pk

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
