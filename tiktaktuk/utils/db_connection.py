# utils/db_connection.py
# Letakkan file ini di root project atau buat folder utils/
# Impor dengan: from utils.db_connection import get_db_connection

import psycopg2
from django.conf import settings


def get_db_connection():
    """
    Mengembalikan koneksi psycopg2 ke database PostgreSQL
    berdasarkan settings.DATABASES['default'].
    """
    db = settings.DATABASES['default']

    conn = psycopg2.connect(
        dbname=db['NAME'],
        user=db['USER'],
        password=db['PASSWORD'],
        host=db['HOST'],
        port=db['PORT'],
    )

    return conn


def extract_trigger_error(exception):
    """
    Mengekstrak pesan error dari RAISE EXCEPTION trigger PostgreSQL.
    psycopg2 membungkus pesan dalam format:
      ERROR:  <pesan trigger>
    Fungsi ini mengembalikan pesan bersih tanpa prefix.
    """
    msg = str(exception)

    # psycopg2 biasanya memformat: 'ERROR:  Username "x" sudah terdaftar...'
    if 'ERROR' in msg:
        # Ambil bagian setelah "ERROR:" terakhir
        parts = msg.split('ERROR')
        clean = parts[-1].strip().lstrip(':').strip()
        # Buang newline dan info tambahan psycopg2
        clean = clean.split('\n')[0].strip()
        return f"ERROR: {clean}"

    return msg