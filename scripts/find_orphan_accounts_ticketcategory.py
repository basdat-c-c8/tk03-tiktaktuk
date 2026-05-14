import sqlite3
con=sqlite3.connect('db.sqlite3')
c=con.cursor()
try:
    c.execute("SELECT category_id, category_name, event_id FROM accounts_ticketcategory WHERE event_id NOT IN (SELECT event_id FROM accounts_event)")
    rows=c.fetchall()
    print('orphan in accounts_ticketcategory count:', len(rows))
    for r in rows:
        print(r)
except Exception as e:
    print('ERR',e)
finally:
    con.close()
