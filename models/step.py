from django.db import models
from django.core.urlresolvers import reverse

from .base import Todo
from .actor import Actor
from .proto import ProtoStep
from .task import Task
from todo.managers import StatusManager
from todo.workflow import (statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES,
                           RESOLUTION_CHOICES)
    
from datetime import datetime

class Step(Todo):
    prototype = models.ForeignKey(ProtoStep, related_name='steps', null=True,
                                  blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True,
                               blank=True)
    task = models.ForeignKey(Task, related_name='steps')
    owner = models.ForeignKey(Actor, null=True, blank=True)
    order = models.PositiveIntegerField()
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)
    _has_children = models.NullBooleanField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last

    objects = StatusManager()
    
    _next = None

    def get_has_children(self):
        if self._has_children is None:
            self._has_children = len(self.children_all()) > 0
        return self._has_children

    def set_has_children(self, value):
        self._has_children = value
        self.save()

    has_children = property(get_has_children, set_has_children)

    class Meta:
        app_label = 'todo'
        ordering = ('order',)

    def __unicode__(self):
        return self.summary

    @property
    def code(self):
        return str(self.id)

    @models.permalink
    def get_absolute_url(self):
        return ('todo.views.task', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/step/%s' % str(self.id)

    def clone(self):
        "Clone the step using the protype used to create it."
        return self.prototype.spawn(summary=self.summary, task=self.task,
                                    parent=self.parent, order=self.order)

    def siblings_all(self):
       """Get a QuerySet with the siblings of the step.
       
       See `todo.models.base.Todo.siblings_all` for more docs.

       """
       if self.parent is None:
           return Step.objects.filter(task=self.task, parent=None)
       else:
           return super(Step, self).siblings_all()

    def next_step(self):
        "Get the step that should be completed after this one."
        if self._next is None:
            try:
                next = self.order + 1
                self._next = self.siblings_all().get(order=next)
            except:
                self._next = None
        return self._next

    def is_last(self):
        return self.next_step() is None

    def activate(self):
        if self.has_children is True:
            self.activate_children()
            # it's `active`, because one of the children is `next`
            self.status = 2
        else:
            # no children, `next` it
            self.status = 3
        self.save()

    def resolve(self, resolution=1, bubble_up=True):
        """Resolve the step.

        Resolve the current step and, if `bubble_up` is True, resolve the
        parent or the parents.

        Arguments:
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
        self.status = 5
        self.resolution = resolution
        self.save()
        if bubble_up:
            if self.parent and (self.is_last() or self.resolves_parent):
                if self.resolution == 2:
                    # if the step has failed, resolve only the immediate parent
                    # and make a fresh copy of it
                    bubble_up = False
                    clone = self.parent.clone()
                    clone.activate()
                if not self.is_any_sibling_status(2, 3):
                    self.parent.resolve(self.resolution, bubble_up)
            elif (self.resolution == 1 and
                  not self.is_last() and
                  self.next_step().status_is('new')):
                self.next_step().activate()
