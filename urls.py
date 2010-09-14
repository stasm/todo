from django.conf.urls.defaults import *

api_patterns = patterns('todo.views.api',
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
)

demo_patterns = patterns('todo.views.demo',
    (r'^combined$', 'combined'),
)

urlpatterns = patterns('todo.views',
    # single task
    (r'^task/(?P<task_id>\d+)$', 'task'),
    (r'^task/(?P<task_id>\d+)/resolve$', 'actions.resolve_task'),
    (r'^step/(?P<step_id>\d+)/resolve$', 'actions.resolve_step'),

    # includes
    (r'^api/', include(api_patterns)),
    (r'^demo/', include(demo_patterns)),
)
