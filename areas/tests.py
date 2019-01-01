from django.test import TestCase

# Create your tests here.
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from .models import Area

class AreaModelTestCase(TestCase):
    def setUp(self):
        User.objects.create(username='Satch')
        Area.objects.create(
            owner=get_object_or_404(User,id=1),
            type='ccodes',
            title='Testy',
            description='how now?',
            id=1,
            ccodes=['ar'],
            geom={}
        )

    def test_area(self):
        obj = Area.objects.get(id=1)
        self.assertEqual(obj.title, 'Testy')
        self.assertEqual(obj.ccodes, ['ar'])
