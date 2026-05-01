from django.db import models
import uuid
from django.contrib.auth.models import User

class Package(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="packages", null=True, blank=True)
    email = models.CharField(max_length=255, default='', blank=False, null=False)
    carrier = models.CharField(max_length=255)
    tracking_number = models.CharField(max_length=255)
    package_status = models.CharField(max_length=255, blank=True, null=True)
    agent_summary = models.TextField(blank=True, null=True)
    events_json = models.TextField(blank=True, null=True)
    coordinates_json = models.TextField(blank=True, null=True) # Store map points
    country = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

