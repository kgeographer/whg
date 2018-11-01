# api.serializers.py

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from contribute.models import Dataset
from main.models import Place


# class DatasetSerializer(serializers.ModelSerializer):
class DatasetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Dataset
        fields = ('owner', 'label', 'name', 'description','format',
            'datatype', 'delimiter', 'status', 'upload_date',
            'accepted_date', 'mapbox_id')

# class PlaceSerializer(serializers.ModelSerializer):
class PlaceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Place
        fields = ('placeid', 'title', 'src_id', 'dataset','ccode')

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
