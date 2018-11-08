# main.models
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.postgres.fields import JSONField

from django.contrib.auth.models import User
from datasets.models import Dataset
import json

class Place(models.Model):
    # let id be auto-maintained, as Django decrees/prefers
    # placeid = models.IntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=255)
    src_id = models.CharField(max_length=24)
    dataset = models.ForeignKey(Dataset, db_column='dataset',
        to_field='label', related_name='datasets', on_delete=models.CASCADE)
    ccode = models.CharField(max_length=2)

    def __str__(self):
        return str(self.id) + '_' + self.title

    class Meta:
        managed = True
        db_table = 'places'
        indexes = [
            models.Index(fields=['src_id', 'dataset']),
        ]

class Source(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    src_id = models.CharField(max_length=24)    # contributor's id
    uri = models.URLField(null=True, blank=True)
    label = models.CharField(max_length=255)    # short, e.g. title, author
    citation = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.label

    class Meta:
        managed = True
        db_table = 'sources'

class PlaceName(models.Model):
    # {toponym, lang, citation{}, when{}}
    place_id = models.ForeignKey(Place, related_name='names',
        default=-1, on_delete=models.CASCADE)
    toponym = models.CharField(max_length=200)
    name_src = models.ForeignKey(Source, null=True, on_delete=models.SET_NULL)
    json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.toponym

    class Meta:
        managed = True
        db_table = 'place_name'


class PlaceType(models.Model):
    # identifier, label, source_label, when{}
    place_id = models.ForeignKey(Place,related_name='types',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)

    def __str__(self):
        return self.label (self.json.source_label)

    class Meta:
        managed = True
        db_table = 'place_type'


class PlaceGeom(models.Model):
    place_id = models.ForeignKey(Place,related_name='geoms',
        default=-1, on_delete=models.CASCADE)
    geom_src = models.ForeignKey(Source, null=True,
        on_delete=models.SET_NULL)
    json = JSONField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'place_geom'


class PlaceLink(models.Model):
    place_id = models.ForeignKey(Place,related_name='links',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # type, identifier

    class Meta:
        managed = True
        db_table = 'place_link'


class PlaceWhen(models.Model):
    place_id = models.ForeignKey(Place,related_name='whens',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # timespans[{start{}, end{}}], periods[{name,id}], label, duration

    class Meta:
        managed = True
        db_table = 'place_when'


class PlaceRelated(models.Model):
    place_id = models.ForeignKey(Place,related_name='related',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # relation_type, relation_to, label, when{}, citation{label,id}, certainty

    class Meta:
        managed = True
        db_table = 'place_related'


class PlaceDescription(models.Model):
    place_id = models.ForeignKey(Place,related_name='descriptions',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # id, value, lang

    class Meta:
        managed = True
        db_table = 'place_description'


class PlaceDepiction(models.Model):
    place_id = models.ForeignKey(Place,related_name='depictions',
        default=-1, on_delete=models.CASCADE)
    json = JSONField(blank=True, null=True)
    # id, title, license

    class Meta:
        managed = True
        db_table = 'place_depiction'
