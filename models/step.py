from django.db import models
from django.core.urlresolvers import reverse

from .action import NEXTED
from .base import Todo
from .actor import Actor
from .project import Project
from .proto import ProtoStep
from .task import Task
from todo.managers import StatusManager
from todo.workflow import (NEW, ACTIVE, NEXT, ON_HOLD, RESOLVED, COMPLETED,
                           FAILED, INCOMPLETE, STATUS_CHOICES,
                           RESOLUTION_CHOICES)
from todo.signals import status_changed
    
from datetime import datetime, timedelta

class Step(Todo):
    prototype = models.ForeignKey(ProtoStep, related_name='steps', null=True,
                                  blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True,
                               blank=True)
    task = models.ForeignKey(Task, related_name='steps')
    project = models.ForeignKey(Project, related_name='steps', null=True,
                                blank=True)
    owner = models.ForeignKey(Actor, null=True, blank=True)
    order = models.PositiveIntegerField()
    status = models.PositiveIntegerField(choices=STATUS_CHOICES, default=NEW)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)
    _has_children = models.NullBooleanField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last
    allowed_time = models.PositiveSmallIntegerField(default=3,
                                        verbose_name="Allowed time (in days)",
                                        help_text="Time the owner has to "
                                                  "complete the step.")
    # a cached string representation of the step
    _repr = models.CharField(max_length=250, blank=True)
    # a cached string representation of the related owner
    owner_repr = models.CharField(max_length=250, blank=True)

    objects = StatusManager()

    class Meta:
        app_label = 'todo'
        ordering = ('order',)

    # a list of additional argument names that can be passed to __init__
    extra_fields = []
    
    def __init__(self, *args, **kwargs):
        # the next step is unknown at this point
        self._next = self
        self._overdue = None
        super(Step, self).__init__(*args, **kwargs)

    def __unicode__(self):
        """Return the cached representation of the object."""
        if not self._repr:
            self._repr = self.summary
            if self.project:
                self._repr = '%s %s' % (self._repr, self.project)
            self.save()
        return self._repr

    def save(self, *args, **kwargs):
        if not self.id and not self.owner_repr and self.owner:
            # the step doesn't exist in the DB yet
            self.owner_repr = unicode(self.owner)
        super(Step, self).save(*args, **kwargs)

    def get_has_children(self):
        if self._has_children is None:
            self._has_children = len(self.children_all()) > 0
        return self._has_children

    def set_has_children(self, value):
        self._has_children = value
        self.save()

    has_children = property(get_has_children, set_has_children)

    @property
    def code(self):
        return str(self.id)

    @models.permalink
    def get_admin_url(self):
        return ('admin:todo_step_change', [self.id])

    def assign_to_projects(self, projects):
        pass

    def clone(self, user):
        "Clone the step using the protype used to create it."
        return self.prototype.spawn(user, summary=self.summary, task=self.task,
                                    parent=self.parent, order=self.order,
                                    project=self.project,
                                    # in case any decendant steps have
                                    # `clone_per_project` set to True
                                    projects=[self.project])

    def children_all(self):
        "Get child steps of the tracker."
        return self.children.all()

    def siblings_all(self):
        """Get a QuerySet with the siblings of the step.
        
        See `todo.models.base.TodoInterface.siblings_all` for more docs.
 
        """
        if self.parent is None:
            return self.task.children_all()
        else:
            return self.parent.children_all()

    def siblings_other(self):
        "Get all siblings except the current object."
        return self.siblings_all().exclude(pk=self.pk)

    def next_step(self):
        "Get the step that should be completed after this one."
        if self._next is self:
            try:
                next = self.order + 1
                self._next = self.siblings_all().get(order=next)
            except:
                self._next = None
        return self._next

    def is_last(self):
        return self.next_step() is None

    def is_only_active(self):
        "Check if there's no more active steps under this step's parent."
        active_siblings = self.siblings_other().filter(status__in=(ACTIVE, NEXT))
        return not bool(active_siblings.count())

    def is_last_open(self):
        "Check if there's no more unresolved steps under this step's parent."
        open_siblings = self.siblings_other().filter(status__lt=RESOLVED)
        return not bool(open_siblings.count() )

    def is_overdue(self):
        if self.status != NEXT:
            # continue only for steps whose status is 'next'
            return False
        if self._overdue is None:
            # FIXME this should be days; minutes are for testing
            allowed_timeinterval = timedelta(minutes=self.allowed_time)
            # get the last time the step was 'nexted'
            last_activity_ts = self.get_latest_action(NEXTED).timestamp
            self._overdue = datetime.now() > (last_activity_ts +
                                              allowed_timeinterval)
        return self._overdue

    def activate(self, user):
        if self.has_children is True:
            self.activate_children(user)
            # it's `active`, because one of the children is `next`
            self.status = ACTIVE
        else:
            # no children, `next` it
            self.status = NEXT
        self.save()
        status_changed.send(sender=self, user=user, flag=self.status)

    def reset_time(self, user):
        if self.status == NEXT:
            # the step must be a 'next' step.  Resetting the timer is simply
            # sending the signal about the step being 'nexted' again.
            status_changed.send(sender=self, user=user, flag=NEXTED)

    def resolve(self, user, resolution=COMPLETED, bubble_up=True):
        """Resolve the step.

        Resolve the current step and, if `bubble_up` is True, resolve the
        parent or the parents.

        Arguments:
        user -- the user that is resolving the step; used for the signal
        resolution -- an integer specifying the resolution type (see
                      todo.workflow)
        bubble_up -- a boolean which if True will make the method resolve the
                     parent(s) of the current step as well.

        More on the `bubble_up` behavior:  When `bubble_up` is True, and if the
        step was resolved successfully and it is the last one among its
        siblings, its parent will be resolved successfully too and if in turn
        the parent is the last one among *its* siblings, the parent's parent
        will be resolved etc.  The resolution *bubbles up*.  On the other hand,
        if the step has failed (note that it must be a review step to be able
        to fail in the first place), the immediate parent of the current step
        is resolved as failed as well and a fresh clone is made so that the
        required actions can take place again.  This time, however, the
        parent's parent is not touched.  The bubbling stops after the first
        parent.

        """
        self.status = RESOLVED
        self.resolution = resolution
        self.save()
        flag = RESOLVED + resolution
        status_changed.send(sender=self, user=user, flag=flag)

        if not bubble_up:
            # don't do anything more
            return
        if ((self.is_last() and self.is_only_active()) or
            self.is_last_open()):
            if self.parent:
                # resolve the parent Step(s)
                if self.resolution == FAILED:
                    # if the step has failed, resolve only the immediate parent
                    # and make a fresh copy of it.  The parent needs to be
                    # a Step, not the Task (can't clone a Task), hence check
                    # for self.parent.
                    bubble_up = False
                    clone = self.parent.clone(user)
                    clone.activate(user)
                self.parent.resolve(user, self.resolution, bubble_up)
            else:
                # no parent means this is a top-level step and the task is
                # possibly ready to be resolved. This left for the user to
                # decide however.
                pass
        elif self.next_step() and self.next_step().status_is('new'):
            self.next_step().activate(user)
