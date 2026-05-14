import sqlite3
con=sqlite3.connect('db.sqlite3')
c=con.cursor()
# check if table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events_ticketcategory'")
if not c.fetchone():
    print('events_ticketcategory table not found; nothing to delete')
else:
    c.execute('SELECT COUNT(*) FROM events_ticketcategory WHERE event_id NOT IN (SELECT event_id FROM accounts_event)')
    cnt = c.fetchone()[0]
    print('orphan_count_before:', cnt)
    if cnt > 0:
        c.execute('DELETE FROM events_ticketcategory WHERE event_id NOT IN (SELECT event_id FROM accounts_event)')
        con.commit()
        print('deleted:', c.rowcount)
    else:
        print('deleted: 0')
    c.execute('SELECT COUNT(*) FROM events_ticketcategory')
    remaining = c.fetchone()[0]
    print('remaining_ticketcategory_rows:', remaining)
con.close()
