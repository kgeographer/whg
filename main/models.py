from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Dataset(models.Model):
    name = models.CharField(max_length=255, null=False)
    slug = models.CharField(max_length=12, null=False, unique="True")
    user = models.ForeignKey(User, on_delete="models.CASCADE")
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.slug

    class Meta:
        managed = True
        db_table = 'datasets'

class Place(models.Model):
    placeid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    src_id = models.CharField(max_length=24, blank=True, null=True)
    dataset = models.ForeignKey(Dataset, db_column='dataset',
        to_field='slug', on_delete="models.CASCADE")

    def __str__(self):
        return self.placeid + '_' + place.title

    class Meta:
        managed = True
        db_table = 'places'
