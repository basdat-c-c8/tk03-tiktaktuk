# views.py (events app)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Artist


def artist_list(request):
    artists = Artist.objects.all().order_by("name")

    context = {
        "artists": artists,

        "total_artists": artists.count(),

        "total_genres": artists.exclude(
            genre__isnull=True
        ).exclude(
            genre=""
        ).values("genre").distinct().count(),

        "total_event": artists.count(),
    }

    return render(
        request,
        "cudartist.html",
        context
    )

def create_artist(request):

    if request.method == "POST":

        name = request.POST.get("name")
        genre = request.POST.get("genre")

        if not name:

            messages.error(
                request,
                "Nama artis wajib diisi."
            )

            return redirect("events:artist_list")

        Artist.objects.create(
            name=name,
            genre=genre
        )

        messages.success(
            request,
            f'Artis "{name}" berhasil ditambahkan.'
        )

        return redirect("events:artist_list")

    return redirect("events:artist_list")

def update_artist(request, id):
    artist = get_object_or_404(
        Artist,
        artist_id=id
    )

    if request.method == "POST":

        name = request.POST.get("name")
        genre = request.POST.get("genre")

        if not name:

            messages.error(
                request,
                "Nama artis wajib diisi."
            )

            return redirect("events:artist_list")

        artist.name = name
        artist.genre = genre
        artist.save()

        messages.success(
            request,
            f'Artis "{name}" berhasil diperbarui.'
        )

        return redirect("events:artist_list")

def delete_artist(request, id):

    artist = get_object_or_404(
        Artist,
        artist_id=id
    )

    if request.method == "POST":

        artist_name = artist.name

        artist.delete()

        messages.success(
            request,
            f'Artis "{artist_name}" berhasil dihapus.'
        )

        return redirect("events:artist_list")

    return redirect("events:artist_list")

def artist_read(request):
    artists = Artist.objects.all().order_by("name")

    context = {
        "artists": artists,

        "total_artists": artists.count(),

        "total_genres": artists.exclude(
            genre__isnull=True
        ).exclude(
            genre=""
        ).values("genre").distinct().count(),

        "total_event": artists.count(),
    }

    return render(
        request,
        "rartist.html",
        context
    )
 
def ticket_category_manage(request):
    return render(request, 'cudticketcategory.html')
 
def ticket_category_read(request):
    return render(request, 'rticketcategory.html')