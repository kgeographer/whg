# api.serializers.py

from django.contrib.auth.models import User, Group
from rest_framework import serializers
from datasets.models import Dataset
from main.models import (Place, PlaceName, PlaceType, PlaceGeom,
    PlaceLink, PlaceRelated, PlaceWhen, PlaceDescription, PlaceDepiction)

class DatasetSerializer(serializers.HyperlinkedModelSerializer):
    places = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all())
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Dataset
        fields = ('id', 'url', 'owner', 'label', 'name', 'description','format',
            'datatype', 'delimiter', 'status', 'upload_date',
            'accepted_date', 'mapbox_id', 'places')


class PlaceDepictionSerializer(serializers.ModelSerializer):
    # json: @id, title, license
    identifier = serializers.ReadOnlyField(source='json.@id')
    title = serializers.ReadOnlyField(source='json.title')
    license = serializers.ReadOnlyField(source='json.license')

    class Meta:
        model = PlaceDepiction
        fields = ('identifier','title','license')


class PlaceDescriptionSerializer(serializers.ModelSerializer):
    # json: @id, value, lang
    identifier = serializers.ReadOnlyField(source='json.@id')
    value = serializers.ReadOnlyField(source='json.value')
    lang = serializers.ReadOnlyField(source='json.lang')

    class Meta:
        model = PlaceDescription
        fields = ('identifier','value','lang')


class PlaceWhenSerializer(serializers.ModelSerializer):
    # json: timespans, periods, label, duration
    timespans = serializers.ReadOnlyField(source='json.timespans')
    periods = serializers.ReadOnlyField(source='json.periods')
    label = serializers.ReadOnlyField(source='json.label')
    duration = serializers.ReadOnlyField(source='json.duration')

    class Meta:
        model = PlaceWhen
        fields = ('timespans', 'periods', 'label', 'duration')


class PlaceRelatedSerializer(serializers.ModelSerializer):
    # json: relation_type, relation_to, label, when, citation, certainty
    relation_type = serializers.ReadOnlyField(source='json.relation_type')
    relation_to = serializers.ReadOnlyField(source='json.relation_to')
    label = serializers.ReadOnlyField(source='json.label')
    when = serializers.ReadOnlyField(source='json.when')
    citation = serializers.ReadOnlyField(source='json.citation')
    certainty = serializers.ReadOnlyField(source='json.certainty')

    class Meta:
        model = PlaceRelated
        fields = ('relation_type', 'relation_to', 'label', 'when',
            'citation', 'certainty')


class PlaceLinkSerializer(serializers.ModelSerializer):
    # json: type, identifier
    type = serializers.ReadOnlyField(source='json.type')
    identifier = serializers.ReadOnlyField(source='json.identifier')

    class Meta:
        model = PlaceLink
        fields = ('type', 'identifier')


class PlaceGeomSerializer(serializers.ModelSerializer):
    # json: type, geowkt, coordinates, when{}
    type = serializers.ReadOnlyField(source='json.type')
    geowkt = serializers.ReadOnlyField(source='json.geowkt')
    coordinates = serializers.ReadOnlyField(source='json.coordinates')
    when = serializers.ReadOnlyField(source='json.when')

    class Meta:
        model = PlaceGeom
        fields = ('type', 'geowkt', 'coordinates', 'geom_src', 'when')


class PlaceTypeSerializer(serializers.ModelSerializer):
    # json: identifier, label, source_label, when{}
    identifier = serializers.ReadOnlyField(source='json.identifier')
    label = serializers.ReadOnlyField(source='json.label')
    source_label = serializers.ReadOnlyField(source='json.src_label')
    when = serializers.ReadOnlyField(source='json.when')

    class Meta:
        model = PlaceType
        fields = ('label', 'source_label', 'when', 'identifier')


class PlaceNameSerializer(serializers.ModelSerializer):
    # json: toponym, citation{}
    toponym = serializers.ReadOnlyField(source='json.toponym')
    citation = serializers.ReadOnlyField(source='json.citation')

    class Meta:
        model = PlaceName
        fields = ('toponym', 'citation')


class PlaceSerializer(serializers.HyperlinkedModelSerializer):
    dataset = serializers.ReadOnlyField(source='dataset.label')
    names = PlaceNameSerializer(many=True, read_only=True)
    types = PlaceTypeSerializer(many=True, read_only=True)
    geoms = PlaceGeomSerializer(many=True, read_only=True)
    links = PlaceLinkSerializer(many=True, read_only=True)
    related = PlaceRelatedSerializer(many=True, read_only=True)
    whens = PlaceWhenSerializer(many=True, read_only=True)
    descriptions = PlaceDescriptionSerializer(many=True, read_only=True)
    depictions = PlaceDepictionSerializer(many=True, read_only=True)

    class Meta:
        model = Place
        fields = ('url','id', 'title', 'src_id', 'dataset','ccodes',
            'names','types','geoms','links','related',
            'whens', 'descriptions', 'depictions')

# for reconciler queries
class PlaceQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ('id','src_id','title','names','types','ccodes')
# {	"placeid" : 10028560,
# 	"src_id" : "1000001",
# 	"prefname" : "Ciudad de Mexico",
# 	"altnames" : ["Ciudad de Mexico","Mexico"],
# 	"geom" : {"type":"MultiPoint","coordinates":[[-99.13313445,19.43378643]]},
# 	"placetypes" : ["inhabited place"],
# 	"countries" : ["MX"],
# 	"province" : "Mexico",
# 	"minmax" : [1521,1808],
# 	"region" : ""
# }

# class UserSerializer(serializers.HyperlinkedModelSerializer):
class UserSerializer(serializers.ModelSerializer):
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
