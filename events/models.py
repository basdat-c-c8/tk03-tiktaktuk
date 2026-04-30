import uuid
from django.db import models


class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=False)
    genre = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'ARTIST'
        ordering = ['name']

    def __str__(self):
        return self.name


class TicketCategory(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50, null=False)
    quota = models.IntegerField(null=False)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=False)

    class Meta:
        db_table = 'TICKET_CATEGORY'
        ordering = ['category_name']

    def __str__(self):
        return self.category_name