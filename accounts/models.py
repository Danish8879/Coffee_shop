from django.db import models
from django.contrib.auth.models import User


# from base.models import BaseModel

class Profile():
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    is_email_verified = models.BooleanField(default=False)
    email_token = models.CharField(max_length=100, null=True,blank=True)
#    profile_image = models.ImageField(upload_to="profile")
