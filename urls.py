from django.conf.urls.defaults import *

api_patterns = patterns('todo.views.api',
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
)

urlpatterns = patterns('todo.views',
    (r'^$', 'index'),
    url(r'^locale/(?P<locale_code>.+)$', 'dashboard', name='todo_locale_dashboard'),
    url(r'^bug/(?P<bug_id>\d+)$', 'dashboard', name='todo_bug_dashboard'),

    # single task
    (r'^(?P<task_id>\d+)$', 'task'),
    (r'^(?P<task_id>\d+)/resolve$', 'actions.resolve_task'),
    (r'^step/(?P<step_id>\d+)/resolve$', 'actions.resolve_step'),

    # new tasks
    (r'^new$', 'new'),

    # includes
    (r'^api/', include(api_patterns)),
)
