from django.db import models
import uuid
import django.utils.timezone

class Package(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    email=models.CharField(max_length=255,default='', blank=False, null=False)
    carrier=models.CharField(max_length=255)
    tracking_number=models.CharField(max_length=255)
    package_status=models.CharField(max_length=255)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

