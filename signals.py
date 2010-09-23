from django.conf import settings
import django.dispatch

from todo.workflow import statuses

# To avoid conflicts with action flags defined in django.contrib.admin.models
# an arbitraty offset is added to every action's index
try:
    OFFSET = int(settings.TODO_LOG_OFFSET)
except (AttributeError, ValueError, TypeError):
    OFFSET = 10
    
UPDATED = 6
SNAPSHOT_UPDATED = 7
BUGID_UPDATED = 8

actions = statuses.copy()
actions.update({
    UPDATED: ('updated',),
    SNAPSHOT_UPDATED: ('snapshot updated',),
    BUGID_UPDATED: ('bugid updated',),
})

# Signal used by `spawn`, `activate` and `resolve` in todo.models.  It handles
# the workflow events, like creating, activating and resolving a todo object.
status_changed = django.dispatch.Signal(providing_args=[
    'user',
    'action',
])

# Signal used by the views in todo.views.api. Handles property changes on
# a todo object (e.g. a change to the summary).
todo_updated = django.dispatch.Signal(providing_args=[
    'user',
    'action',
])

def receiver(signal, **kwargs):
    """A decorator for connecting receivers to signals. 
    
    Taken from Django 1.2.  Used by passing in the signal and keyword arguments
    to connect::

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        signal.connect(func, **kwargs)
        return func
    return _decorator
