import uuid
from django.db import models

# Create your models here.
class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=False)
    genre = models.CharField(max_length=100, blank=True, null=True)
 
    class Meta:
        db_table = 'ARTIST'
        ordering = ['name']
 
    def __str__(self):
        return self.name