from django.db import models
from django.db.models import Q
from django.contrib.contenttypes import generic

from .action import Action, ACTIVATED, UPDATED
from todo.workflow import NEW, ACTIVE, NEXT
from todo.signals import status_changed, todo_updated

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
    actions = generic.GenericRelation(Action, object_id_field="subject_id",
                                    content_type_field="subject_content_type")

    class Meta:
        app_label ='todo'
        abstract = True

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status in (NEW, ACTIVE, NEXT)

    def is_next(self):
        return self.status == NEXT

    def get_actions(self, flag=None):
        if flag is None:
            return self.actions.all()
        return self.actions.filter(flag=flag)

    def get_latest_action(self, flag=None):
        return self.get_actions(flag).latest('timestamp')

    def activate(self, user):
        self.activate_children(user)
        self.status = ACTIVE
        self.save()
        status_changed.send(sender=self, user=user, flag=ACTIVATED)

    def activate_children(self, user):
        to_activate = self.children_all().filter(Q(is_auto_activated=True) |
                                                 Q(order=1))
        if len(to_activate) == 0:
            to_activate = self.children_all()
        for child in to_activate:
            child.activate(user)

    def update(self, user, properties, send_signal=True, flag=UPDATED):
        """Update properties of the todo object.

        Arguments:
            user -- the author of the change
            properties -- a dict with new values for the properties
            send_signal -- a boolean defining whether to send a `todo_updated`
                           signal or not (default is True)
            flag -- a flag to be sent in the signal (default is UPDATED)

        """
        for prop, new_value in properties.iteritems():
            setattr(self, prop, new_value)
        self.save()
        if send_signal:
            todo_updated.send(sender=self, user=user, flag=flag)
