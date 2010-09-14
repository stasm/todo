from django.conf.urls.defaults import *

action_patterns = patterns('todo.views.actions',
    (r'^resolve/task/(?P<task_id>\d+)$', 'resolve_task'),
    (r'^resolve/step/(?P<step_id>\d+)$', 'resolve_step'),
)

api_patterns = patterns('todo.views.api',
    # move this to actions
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
)

demo_patterns = patterns('todo.views.demo',
    (r'^task/(?P<task_id>\d+)$', 'task'), # document this. apps need to have this
    (r'^combined$', 'combined'),
)

urlpatterns = patterns('',
    # includes
    (r'^action/', include(action_patterns)),
    (r'^api/', include(api_patterns)),
    (r'^demo/', include(demo_patterns)),
)
