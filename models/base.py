from django.db import models
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes import generic
from django.contrib.admin.models import LogEntry

from todo.signals import OFFSET, status_changed

class TodoInterface(object):
    """An interface class for all todo objects."""

    def __unicode__(self):
        raise NotImplementedError()

    @property
    def code(self):
        raise NotImplementedError()

    def get_admin_url(self):
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=600544
        raise NotImplementedError()

    def children_all(self):
        """Get the immediate children of the todo object.

        In its simplest form, this method just calls `all` on the todo object's
        `children` manager.  It does more if called on a Task.  By calling
        `children_all` you make sure that the returned value is a QuerySet, no
        matter which model's instance you called it on.

        See todo.models.Task.children_all for more docs.
        
        """
        raise NotImplementedError()

    def siblings_all(self):
        """Get a QuerySet with the siblings of the current todo object.
        
        Since it returns a QuerySet, the name is `siblings_all` rather than
        `siblings`, in order to help avoid confusion (similar to `children_all`
        above).
 
        """
        raise NotImplementedError()

    def clone(self):
        raise NotImplementedError()

    def resolve(self):
        raise NotImplementedError()

    def activate(self):
        raise NotImplementedError()

class Todo(TodoInterface, models.Model):
    """Common methods for all todo objects (trackers, tasks, steps)"""

    # signals log actions using LogEntry
    actions = generic.GenericRelation(LogEntry)

    class Meta:
        app_label ='todo'
        abstract = True

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status in (1, 2, 3)

    def is_next(self):
        return self.status == 3

    def get_actions(self, action_flag=None):
        if action_flag is None:
            return self.actions.all()
        offset_flag = action_flag + OFFSET
        return self.actions.filter(action_flag=offset_flag)

    def get_latest_action(self, action_flag=None):
        return self.get_actions(action_flag).latest('action_time')

    def activate(self, user):
        self.activate_children(user)
        self.status = 2
        self.save()
        status_changed.send(sender=self, user=user, action=self.status)

    def activate_children(self, user):
        to_activate = self.children_all().filter(Q(is_auto_activated=True) |
                                                 Q(order=1))
        if len(to_activate) == 0:
            to_activate = self.children_all()
        for child in to_activate:
            child.activate(user)
