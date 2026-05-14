import sqlite3
con=sqlite3.connect('db.sqlite3')
c=con.cursor()
print('accounts_event rows:')
for row in c.execute('select event_id,event_title from accounts_event'):
    print(row)
print('\nevents_ticketcategory rows:')
for row in c.execute('select category_id,category_name,event_id from events_ticketcategory'):
    print(row)
con.close()
