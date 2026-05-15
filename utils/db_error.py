def extract_trigger_error(exception):
    """
    Mengambil pesan RAISE EXCEPTION dari trigger PostgreSQL.
    
    Trigger PostgreSQL melempar pesan dengan format:
      'ERROR: <pesan kita>\nCONTEXT: ...'
    
    Fungsi ini mengambil hanya bagian '<pesan kita>'.
    """
    error_str = str(exception)
    if 'ERROR:' in error_str:
        clean = error_str.split('ERROR:')[-1].split('\n')[0].strip()
        return f'ERROR: {clean}'
    return 'Terjadi kesalahan pada database.'