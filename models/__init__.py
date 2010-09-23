from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
try:
    from django.dispatch import receiver
except ImportError:
    from todo.signals import receiver

from todo.signals import OFFSET, actions, status_changed, todo_updated

@receiver(todo_updated)
@receiver(status_changed)
def log_status_change(sender, user, action, **kwargs):
    LogEntry.objects.log_action(
        user_id = user.pk,
        content_type_id = ContentType.objects.get_for_model(sender).pk,
        object_id = sender.pk,
        object_repr = '%s: %s' % (unicode(sender), actions[action][0]),
        action_flag = action + OFFSET,
        change_message = actions[action][0]
    )

from .project import Project
from .actor import Actor
from .proto import *
from .tracker import Tracker
from .task import Task
from .step import Step
