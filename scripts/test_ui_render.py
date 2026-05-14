from django.conf import settings
settings.ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
from django.contrib.auth.models import User
from django.test import Client

# use existing test user created earlier
c = Client()
logged = c.login(username='testcust', password='pass')
print('login:', logged)

resp = c.get('/orders/create/')
print('GET /orders/create/ status:', resp.status_code)

resp2 = c.get('/tickets/')
print('GET /tickets/ status:', resp2.status_code)
content = resp2.content.decode('utf-8')
print('tickets page length:', len(content))
# print a snippet
print(content[:500])
