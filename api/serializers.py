# api.serializers.py

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from contribute.models import Dataset
from main.models import Place,PlaceName,PlaceType


class DatasetSerializer(serializers.HyperlinkedModelSerializer):
    places = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all())
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Dataset
        fields = ('id', 'url', 'owner', 'label', 'name', 'description','format',
            'datatype', 'delimiter', 'status', 'upload_date',
            'accepted_date', 'mapbox_id', 'places')

class PlaceTypeSerializer(serializers.ModelSerializer):
    # identifier, label, source_label, when{}
    identifier = serializers.ReadOnlyField(source='json.identifier')
    label = serializers.ReadOnlyField(source='json.label')
    source_label = serializers.ReadOnlyField(source='json.source_label')
    when = serializers.ReadOnlyField(source='json.when')

    class Meta:
        model = PlaceType
        fields = ('label', 'source_label', 'when', 'identifier')

class PlaceNameSerializer(serializers.ModelSerializer):
    # toponym, citation{}
    toponym = serializers.ReadOnlyField(source='json.toponym')
    citation = serializers.ReadOnlyField(source='json.citation')

    class Meta:
        model = PlaceName
        fields = ('toponym', 'citation')

# class PlaceSerializer(serializers.ModelSerializer):
class PlaceSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.ReadOnlyField(source='dataset.label')

    names = PlaceNameSerializer(many=True, read_only=True)
    types = PlaceTypeSerializer(many=True, read_only=True)
    # geom = PlaceGeomSerializer(many=True, read_only=True)
    # links = PlaceLinkSerializer(many=True, read_only=True)
    # relations = PlaceRelationSerializer(many=True, read_only=True)
    # whens = PlaceWhenSerializer(many=True, read_only=True)
    # descriptions = PlaceDescriptionSerializer(many=True, read_only=True)
    # depictions = PlaceDepictionSerializer(many=True, read_only=True)

    class Meta:
        model = Place
        fields = ('url','placeid', 'title', 'src_id', 'dataset','ccode',
            'names' , 'types')
            # , 'geoms', 'links', 'relations',
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
