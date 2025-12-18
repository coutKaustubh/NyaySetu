from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_lawyer = models.BooleanField(default=False)
    contact_number = models.CharField(max_length=15)
