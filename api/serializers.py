# api.serializers.py

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from contribute.models import Dataset
from main.models import Place,PlaceName,PlaceType


# class DatasetSerializer(serializers.ModelSerializer):
class DatasetSerializer(serializers.HyperlinkedModelSerializer):
    places = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all())
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Dataset
        fields = ('id', 'url', 'owner', 'label', 'name', 'description','format',
            'datatype', 'delimiter', 'status', 'upload_date',
            'accepted_date', 'mapbox_id', 'places')

# class PlaceNameSerializer(serializers.HyperlinkedModelSerializer):
class PlaceNameSerializer(serializers.ModelSerializer):
    toponym = serializers.ReadOnlyField(source='json.toponym')
    citation = serializers.ReadOnlyField(source='json.citation')

    class Meta:
        model = PlaceName
        # fields = ('json',)
        fields = ('toponym', 'citation')

# class PlaceSerializer(serializers.ModelSerializer):
class PlaceSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.ReadOnlyField(source='dataset.label')

    names = PlaceNameSerializer(many=True, read_only=True)

    # types = serializers.StringRelatedField(source='types.json',many=True)
    # geoms = serializers.StringRelatedField(source='geoms.json',many=True)
    # links = serializers.StringRelatedField(source='links.json',many=True)
    # relations = serializers.StringRelatedField(source='relations.json',many=True)
    # whens = serializers.StringRelatedField(source='whens.json',many=True)
    # descriptions = serializers.StringRelatedField(source='descriptions.json',many=True)
    # depictions = serializers.StringRelatedField(source='depictions.json',many=True)

    class Meta:
        model = Place
        fields = ('url','placeid', 'title', 'src_id', 'dataset','ccode',
            'names')
            # , 'types', 'geoms', 'links', 'relations',
            # 'whens', 'descriptions', 'depictions')

class UserSerializer(serializers.ModelSerializer):
# class UserSerializer(serializers.HyperlinkedModelSerializer):
    datasets = serializers.PrimaryKeyRelatedField(
        many=True,
        read_only=True
    )

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups', 'datasets')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
