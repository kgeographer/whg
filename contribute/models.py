# contribute.models
from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User
# from main.models import Place
from .choices import *

def user_directory_path(instance, filename):
    # upload to MEDIA_ROOT/user_<username>/<filename>
    return 'user_{0}/{1}'.format(instance.owner.username, filename)

# TODO: multiple files per dataset w/File model and formset
class Dataset(models.Model):
    label = models.CharField(max_length=20, null=False, unique="True")
    name = models.CharField(max_length=255, null=False)
    description = models.CharField(max_length=2044, null=False)
    file = models.FileField(upload_to=user_directory_path)
    format = models.CharField(max_length=12, null=False,choices=FORMATS,
        default='csv')
    datatype = models.CharField(max_length=12, null=False,choices=DATATYPES,
        default='place')
    status = models.CharField(max_length=12, null=True, blank=True, choices=STATUS)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(null=True, auto_now_add=True)
    accepted_date = models.DateTimeField(null=True, auto_now_add=True)
    mapbox_id = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.label

    class Meta:
        managed = True
        db_table = 'datasets'

    def get_absolute_url(self):
        return reverse('ds_edit', kwargs={'pk': self.pk})

@receiver(pre_delete, sender=Dataset)
def remove_file(**kwargs):
    instance = kwargs.get('instance')
    instance.file.delete(save=False)


class Authority(models.Model):
	name = models.CharField(choices=AUTHORITIES, max_length=64)
	base_uri = models.CharField(max_length=255)

	def __str__(self):
		return str(self.name)

	class Meta:
		managed = True
		db_table = 'authorities'

# product of hit validation
class Link(models.Model):
    # WHG identifier
    placeid = models.ForeignKey('main.Place', on_delete="models.CASCADE")

    # contributor identifier
    src_id = models.CharField(max_length=24)

    authority = models.ForeignKey(Authority, db_column='authority',
        to_field='id', on_delete="models.CASCADE")

    # authority place record identifier
    authrecord_id = models.CharField(max_length=64)
    match_type = models.CharField(max_length=12, choices=AUTHORITIES )
    review_note = models.CharField(max_length=2044, blank=True, null=True)
    flag_geom = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    def __str__(self):
    	return str(self.id)

    class Meta:
    	managed = True
    	db_table = 'links'

# raw hits from reconciliation
class Hit(models.Model):
    placeid = models.ForeignKey('main.Place', on_delete="models.CASCADE")
    authority = models.ForeignKey(Authority, db_column="authority", to_field="id", on_delete="models.CASCADE")

    # authority place record identifier
    authrecord_id = models.CharField(max_length=64)

    # json response; parse later according to authority
    result = JSONField(blank=True, null=True)

    def __str__(self):
    	return str(self.id)

    class Meta:
    	managed = True
    	db_table = 'hits'
