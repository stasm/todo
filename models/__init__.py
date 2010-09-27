from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
try:
    from django.dispatch import receiver
except ImportError:
    from todo.signals import receiver

from todo.signals import OFFSET, actions, status_changed, todo_updated

from .project import Project
from .actor import Actor
from .proto import *
from .tracker import Tracker, TrackerInProject
from .task import Task, TaskInProject
from .step import Step

@receiver(todo_updated)
@receiver(status_changed)
def log_status_change(sender, user, action, **kwargs):
    """Create a log entry describing the change.

    The logging backend is the default Django's admin one. Log entries are
    available via an `actions` property on todo objects, which returns
    a manager.

    For efficiency reasons, in case of Steps, the resolution time is cached on
    the corresponding Task as well, in `Task.latest_resolution_ts`. It is thus
    readily available for quick queries.

    """
    LogEntry.objects.log_action(
        user_id = user.pk,
        content_type_id = ContentType.objects.get_for_model(sender).pk,
        object_id = sender.pk,
        object_repr = '%s: %s' % (unicode(sender), actions[action][0]),
        action_flag = action + OFFSET,
        change_message = actions[action][0]
    )

    if isinstance(sender, Step) and action == 5:
        # a Step has just been resolved, let's store the time of this change on
        # the related Task for faster queries.

        # why on Earth don't log_action return what it created?! :/
        tstamp = sender.get_latest_action(5).action_time
        sender.task.latest_resolution_ts = tstamp
        sender.task.save()
        # don't send the signal about the task being changed, it's not worth it
