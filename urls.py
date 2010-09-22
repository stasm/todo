from django.conf.urls.defaults import *

action_patterns = patterns('todo.views.actions',
    (r'^resolve/task/(?P<task_id>\d+)$', 'resolve_task'),
    (r'^resolve/step/(?P<step_id>\d+)$', 'resolve_step'),
)

# the API views return JSON responses
api_patterns = patterns('todo.views.api',
    (r'^task/(?P<task_id>\d+)/update-snapshot$', 'update_snapshot'),
    (r'^task/(?P<task_id>\d+)/update-bugid$', 'update_bugid'),
    (r'^task/(?P<obj_id>\d+)/update$', 'update', {'obj': 'task'},
     'todo-api-update-task'),
    (r'^tracker/(?P<obj_id>\d+)/update$', 'update', {'obj': 'tracker'},
     'todo-api-update-tracker'),
)

# demo views are used for testing and as an example for the real views
# that an application wishing to have todo needs to implement
demo_patterns = patterns('todo.views.demo',
    (r'^task/(?P<task_id>\d+)$', 'task'),
    (r'^combined$', 'combined'),
    (r'^tracker/(?P<tracker_id>\d+)$', 'tracker'),
    (r'^trackers$', 'trackers'),
)

urlpatterns = patterns('',
    (r'new/$', 'todo.views.new'),
    (r'new/tasks$', 'todo.views.create', {'obj': 'tasks'},
     'todo-create-tasks'),
    (r'new/trackers$', 'todo.views.create', {'obj': 'trackers'},
     'todo-create-trackers'),
    # includes
    (r'^action/', include(action_patterns)),
    (r'^api/', include(api_patterns)),
    (r'^demo/', include(demo_patterns)),
)
