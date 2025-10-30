# app/models.py
from django.db import models
from django.utils import timezone

class City(models.Model):
    name = models.CharField(max_length=128, unique=True)
    email = models.EmailField(blank=True, null=True)

    # latest weather snapshot
    last_temp = models.FloatField(null=True, blank=True)
    last_desc = models.CharField(max_length=255, null=True, blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
