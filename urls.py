from django.conf.urls.defaults import *
from todo.feeds import NewTasksFeed, NewNextActionsFeed

feeds = {
    'tasks': NewTasksFeed,
    'nextactions': NewNextActionsFeed,
}

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    (r'^dashboard$', 'dashboard'),
    (r'^task/(?P<task_id>\d+)$', 'task'),
    (r'^(?P<todo_id>\d+)/resolve$', 'resolve'),
    (r'^new$', 'new'),
    (r'^new/create$', 'create'),
    (r'^api/tasks$', 'tasks_json'),
)

urlpatterns += patterns('',
    (r'^feed/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
)
