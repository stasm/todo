from django.conf.urls.defaults import *

api_patterns = patterns('todo.views.api',
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
)

demosnippet_patterns = patterns('todo.views.snippets',
    (r'^combined/(?P<project_code>.+)/(?P<locale_code>.+)/?$', 'combined_demo'),
)

urlpatterns = patterns('todo.views',
    # single task
    (r'^(?P<task_id>\d+)$', 'task'),
    (r'^(?P<task_id>\d+)/resolve$', 'actions.resolve_task'),
    (r'^step/(?P<step_id>\d+)/resolve$', 'actions.resolve_step'),

    # includes
    (r'^api/', include(api_patterns)),
    (r'^demosnippet/', include(demosnippet_patterns)),
)
