from django.db import models


class Place(models.Model):
    placeid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    src_id = models.CharField(max_length=24, blank=True, null=True)
    dataset = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'places'


class Dataset(models.Model):
    name = models.CharField(max_length=255, null=False)
    label = models.CharField(max_length=10, null=False)

    def __str__(self):
        return self.label
    class Meta:
        managed = True
        db_table = 'datasets'
