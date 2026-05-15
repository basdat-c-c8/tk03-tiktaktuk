import uuid
from django.db import models


class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name      = models.CharField(max_length=100)
    genre     = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'artist'
        ordering = ['name']

    def __str__(self):
        return self.name


class EventArtist(models.Model):
    event  = models.ForeignKey('accounts.Event', on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    role   = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'event_artist'
        unique_together = ("event", "artist")

    def __str__(self):
        return f"{self.event} – {self.artist}"


class TicketCategory(models.Model):
    category_id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50)
    quota         = models.IntegerField()
    price         = models.DecimalField(max_digits=12, decimal_places=2)
    event         = models.ForeignKey(
        'accounts.Event',
        on_delete=models.CASCADE,
        related_name='ticket_categories',
    )

    class Meta:
        db_table = 'ticket_category'
        ordering = ['event__event_title', 'category_name']

    def __str__(self):
        return f"{self.category_name} – {self.event.event_title}"