from django.conf.urls.defaults import *

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    (r'^new$', 'new'),
    (r'^new/create$', 'create'),
    (r'^(?P<todo_id>\d+)/created/$', 'created'),
    (r'^(?P<todo_id>\d+)/$', 'details'),
    (r'^(?P<todo_id>\d+)/change/$', 'change'),
    (r'^(?P<todo_id>\d+)/changed/$', 'changed'),
)
