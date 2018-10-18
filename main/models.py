from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch import receiver

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_{0}/{1}'.format(instance.user.username, filename)
    # TODO: switch to username for folders
    # return 'user_{0}/{1}'.format(instance.user.username, filename)

class Dataset(models.Model):
    name = models.CharField(max_length=255, null=False)
    slug = models.CharField(max_length=12, null=False, unique="True")
    user = models.ForeignKey(User, on_delete="models.CASCADE")
    file = models.FileField(upload_to=user_directory_path)
    description = models.CharField(max_length=2044, null=False)
    # TODO:
    uploaded = models.DateTimeField(null=True, auto_now_add=True)

    def __str__(self):
        return self.slug

    class Meta:
        managed = True
        db_table = 'datasets'

    def get_absolute_url(self):
        return reverse('ds_edit', kwargs={'pk': self.pk})

@receiver(pre_delete, sender=Dataset)
def remove_file(**kwargs):
    instance = kwargs.get('instance')
    instance.file.delete(save=False)

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
