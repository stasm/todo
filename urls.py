from django.conf.urls.defaults import *

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    (r'^dashboard$', 'dashboard'),
    (r'^task/(?P<task_id>\d+)$', 'task'),
    (r'^(?P<todo_id>\d+)/resolve$', 'resolve'),
    (r'^new$', 'new'),
    (r'^new/create$', 'create'),
    (r'^api/tasks$', 'tasks_json'),
)
