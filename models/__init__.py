try:
    from django.dispatch import receiver
except ImportError:
    from todo.signals import receiver

from todo.workflow import RESOLVED
from todo.signals import status_changed, todo_updated

from .action import Action
from .project import Project
from .actor import Actor
from .proto import *
from .tracker import Tracker, TrackerInProject
from .task import Task, TaskInProject
from .step import Step

@receiver(todo_updated)
@receiver(status_changed)
def log_status_change(sender, user, flag, **kwargs):
    """Create a log entry describing the change.

    The logging backend is the default Django's admin one. Log entries are
    available via an `actions` property on todo objects, which returns
    a manager.

    For efficiency reasons, in case of Steps, the resolution time is cached on
    the corresponding Task as well, in `Task.latest_resolution_ts`. It is thus
    readily available for quick queries.

    """
    action = Action.objects.log(user, sender, flag)

    if isinstance(sender, Step) and action >= RESOLVED:
        # a Step has just been resolved, let's store the time of this change on
        # the related Task for faster queries. We don't need to send the signal
        # again for the task as the action has already been recorded for the
        # step.
        sender.task.update(user, {'latest_resolution_ts': action.timestamp},
                           send_signal=False)
