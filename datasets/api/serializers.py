from rest_framework import serializers

from datasets.models import Dataset
from main.models import Place

class DatasetSerializer(serializers.HyperlinkedModelSerializer):
    places = serializers.PrimaryKeyRelatedField(many=True, queryset=Place.objects.all())
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Dataset
        fields = ('id', 'url', 'owner', 'label', 'name', 'description','format',
            'datatype', 'delimiter', 'status', 'upload_date',
            'accepted_date', 'mapbox_id', 'places')
