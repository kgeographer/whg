# api.views
from django.contrib.auth.models import User, Group
from rest_framework import generics
from rest_framework import permissions
from rest_framework import viewsets

from .serializers import UserSerializer, GroupSerializer, DatasetSerializer, \
    PlaceSerializer


from accounts.permissions import IsOwnerOrReadOnly, IsOwner
from datasets.models import Dataset
from main.models import Place #, PlaceName, PlaceType

class DatasetViewSet(viewsets.ModelViewSet):
    # print('in DatasetViewSet()')
    queryset = Dataset.objects.all().order_by('label')
    # TODO: public list only accepted datasets
    # queryset = Dataset.objects.exclude(accepted_date__isnull=True).order_by('label')
    serializer_class = DatasetSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list','retrieve']:
            print(self.action)
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


class PlaceViewSet(viewsets.ModelViewSet):
    # print('in PlaceViewSet()')
    queryset = Place.objects.all().order_by('title')
    serializer_class = PlaceSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        qs = Place.objects.all()
        query = self.request.GET.get('q')
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
