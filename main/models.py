# main.models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField

from contribute.models import Dataset

class Place(models.Model):
    placeid = models.IntegerField(primary_key=True)
    # placeid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    ccode = models.CharField(max_length=2)

    def __str__(self):
        return str(self.placeid) + '_' + self.title

    class Meta:
        managed = True
        db_table = 'places'
        indexes = [
            models.Index(fields=['src_id', 'dataset']),
        ]

class PlaceName(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    toponym = models.CharField(max_length=200)
    json = JSONField(blank=True, null=True)
	# toponym, lang, citation{}, when{}

    def __str__(self):
        return str(self.placeid) + '-' + self.toponym

    class Meta:
        managed = True
        db_table = 'place_name'


class PlaceType(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # identifier, label, source_label, when{}

    class Meta:
        managed = True
        db_table = 'place_type'


class PlaceGeom(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # type, geometries[{type,coordinates,geowkt,when{},source}], when{}

    class Meta:
        managed = True
        db_table = 'place_geom'


class PlaceWhen(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # timespans[{start{}, end{}}], periods[{name,id}], label, duration

    class Meta:
        managed = True
        db_table = 'place_when'


class PlaceLink(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # type, identifier

    class Meta:
        managed = True
        db_table = 'place_link'


class PlaceRelated(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # relation_type, relation_to, label, when{}, citation{label,id}, certainty

    class Meta:
        managed = True
        db_table = 'place_related'


class PlaceDescription(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # id, value, lang

    class Meta:
        managed = True
        db_table = 'place_description'


class PlaceDepiction(models.Model):
    placeid = models.ForeignKey(Place,on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey('contribute.Dataset', db_column='dataset',
        to_field='label', on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # id, title, license

    class Meta:
        managed = True
        db_table = 'place_depiction'
