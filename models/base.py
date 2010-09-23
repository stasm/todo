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

    def get_absolute_url(self):
        raise NotImplementedError()

    def get_admin_url(self):
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

    def __init__(self, *args, **kwargs):
        """Initialize a todo object.

        The logic in this method is related to trackers and tasks.  Steps do
        not have the `suffix`, `alias` and `project` attributes.

        The method accepts one additional argument besides the ones defined by
        the model definiton: `suffix`.  If given, it will be appended to the
        parent's or the project's `alias` to create the current todo's alias.
        This provides a breadcrumbs-like functionality.

        Alternatively, you can pass `alias` directly, which will make the
        method ignore the `suffix` and set `self.alias` to the value passed.

        """
        suffix = kwargs.pop('suffix', None)
        if suffix is not None and 'alias' not in kwargs:
            if 'parent' in kwargs and kwargs['parent'] is not None:
                kwargs['alias'] = kwargs['parent'].alias + suffix
            elif 'project' in kwargs and kwargs['project'] is not None:
                kwargs['alias'] = kwargs['project'].code + suffix
            else:
                raise TypeError("You must specify a `parent` and/or a "
                                "`project` when passing a `suffix`. Or, pass "
                                "an `alias`, which will be set on the todo "
                                "object unaltered.")
        super(Todo, self).__init__(*args, **kwargs)

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status in (1, 2, 3)

    def is_next(self):
        return self.status == 3

    def get_actions(self, action_flag):
        offset_flag = action_flag + OFFSET
        return self.actions.filter(action_flag=offset_flag)

    def get_latest_action(self, action_flag):
        return self.get_actions(action_flag).latest('action_time')

    def children_all(self):
        """Get the immediate children of the todo object.

        In its simplest form, this method just calls `all` on the todo object's
        `children` manager.  It does more if called on a Task.  By calling
        `children_all` you make sure that the returned value is a QuerySet, no
        matter which model's instance you called it on.
        
        Backstory:  Tasks do not have the `children` manager, and instead, you
        need to query for Steps with no parent (because only other Steps can be
        Steps' parents).  Since you make an actual query, you get a queryset,
        so the behavior is inconsistent with that of accessing `children` on
        Steps and Tracker (which returns a manager).

        """
        return self.children.all()

    def siblings_all(self):
       """Get a QuerySet with the siblings of the current todo object.
       
       Since it returns a QuerySet, the name is `siblings_all` rather than
       `siblings`, in order to help avoid confusion (similar to `children_all`
       above).

       """
       return self.parent.children_all()

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
