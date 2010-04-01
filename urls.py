from django.conf.urls.defaults import *
from todo.feeds import NewTasksFeed, NewNextActionsFeed

feeds = {
    'tasks': NewTasksFeed,
    'next': NewNextActionsFeed,
}

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    url(r'^all$', 'dashboard', name='todo_dashboard'),
    url(r'^locale/(?P<locale_code>.+)$', 'dashboard', name='todo_locale_dashboard'),
    url(r'^project/(?P<project_slug>.+)$', 'dashboard', name='todo_project_dashboard'),
    (r'^(?P<task_id>\d+)$', 'task'),
    (r'^(?P<todo_id>\d+)/resolve$', 'resolve'),
    (r'^new$', 'new'),
    (r'^new/create$', 'create'),
    (r'^api/tasks$', 'tasks_json'),
    
    # used by {% url %} for reverse look-ups in the exhibit
    url(r'^locale/$', 'dashboard', name='todo_locale_dashboard_exhibit'),
    url(r'^project/$', 'dashboard', name='todo_project_dashboard_exhibit'),
    url(r'^$', 'index', name='todo_task_exhibit'),
)

urlpatterns += patterns('',
    (r'^feed/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
)
