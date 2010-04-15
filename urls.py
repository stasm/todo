from django.conf.urls.defaults import *
from todo.feeds import NewTasksFeed, NewNextActionsFeed

feeds = {
    'tasks': NewTasksFeed,
    'next': NewNextActionsFeed,
}

api_patterns = patterns('todo.api',
    (r'^tasks$', 'tasks'),
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
    (r'^existing-bugs$', 'existing_bugs'),
)

feed_patterns = patterns('',
    (r'^builder$', 'todo.views.feed_builder'),
    (r'^show$', 'todo.views.redirect_to_feed'),
    (r'^(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
)

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    url(r'^project/(?P<project_slug>.+)/summary$', 'project_summary', name='todo_project_summary'),
    # dashboards
    url(r'^everything$', 'dashboard', name='todo_dashboard'),
    url(r'^locale/(?P<locale_code>.+)/(?P<status>.+)$', 'dashboard', name='todo_locale_dashboard_status'),
    url(r'^locale/(?P<locale_code>.+)$', 'dashboard', name='todo_locale_dashboard'),
    url(r'^project/(?P<project_slug>.+)/(?P<status>.+)$', 'dashboard', name='todo_project_dashboard_status'),
    url(r'^project/(?P<project_slug>.+)$', 'dashboard', name='todo_project_dashboard'),
    url(r'^bug/(?P<bug_id>\d+)/(?P<status>.+)$', 'dashboard', name='todo_bug_dashboard_status'),
    url(r'^bug/(?P<bug_id>\d+)$', 'dashboard', name='todo_bug_dashboard'),
    # single task
    (r'^(?P<task_id>\d+)$', 'task'),
    (r'^(?P<todo_id>\d+)/resolve$', 'resolve'),
    # new tasks
    (r'^new$', 'new'),
    (r'^new/manually$', 'new_manually'),
    (r'^new/create$', 'create'),
    # includes
    (r'^api/', include(api_patterns)),
    (r'^feed/', include(feed_patterns)),
    
    
    # used by {% url %} for reverse look-ups in the exhibit
    url(r'^locale/$', 'dashboard', name='todo_locale_dashboard_exhibit'),
    url(r'^project/$', 'dashboard', name='todo_project_dashboard_exhibit'),
    url(r'^bug/$', 'dashboard', name='todo_bug_dashboard_exhibit'),
    url(r'^$', 'index', name='todo_task_exhibit'),
)
