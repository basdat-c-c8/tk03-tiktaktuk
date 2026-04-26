import uuid
from django.db import models
from django.contrib.auth.models import User


class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.role_name


class AccountRole(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("role", "user")

    def __str__(self):
        return f"{self.user.username} - {self.role.role_name}"


class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.full_name


class Organizer(models.Model):
    organizer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100, blank=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.organizer_name


class Venue(models.Model):
    venue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue_name = models.CharField(max_length=100)
    capacity = models.IntegerField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    has_reserved_seating = models.BooleanField(default=False)

    def __str__(self):
        return self.venue_name


class Seat(models.Model):
    seat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=50)
    seat_number = models.CharField(max_length=10)
    row_number = models.CharField(max_length=10)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.section} - Row {self.row_number} Seat {self.seat_number}"
    
class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    genre = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_datetime = models.DateTimeField()
    event_title = models.CharField(max_length=200)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    organizer = models.ForeignKey(Organizer, on_delete=models.CASCADE)
    artists = models.ManyToManyField(Artist, through="EventArtist")
    description = models.TextField(blank=True)

    def __str__(self):
        return self.event_title


class EventArtist(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("event", "artist")


class TicketCategory(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50)
    quota = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_categories")

    def __str__(self):
        return self.category_name
    