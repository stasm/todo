from django.db import models
from django.core.urlresolvers import reverse

from .base import Todo
from .actor import Actor
from .proto import ProtoStep
from .task import Task
from todo.managers import StatusManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
    
from datetime import datetime

class Step(models.Model, Todo):
    prototype = models.ForeignKey(ProtoStep, related_name='steps', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    task = models.ForeignKey(Task, related_name='steps')
    owner = models.ForeignKey(Actor, null=True, blank=True)
    order = models.PositiveIntegerField()
    
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES, null=True, blank=True)
    
    _has_children = models.NullBooleanField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last

    objects = StatusManager()
    
    _next = None

    def get_has_children(self):
        if self._has_children is None:
            self._has_children = len(self.children.all()) > 0
        return self._has_children

    def set_has_children(self, value):
        self._has_children = value

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
        return self.prototype.spawn(summary=self.summary, task=self.task,
                                    parent=self.parent, order=self.order)

    @property
    def siblings(self):
       if self.parent is None:
           return Step.objects.filter(task=self.task, parent=None)
       else:
           return super(Step, self).siblings

    @property
    def next(self):
        if self._next is None:
            try:
                next = self.order + 1
                self._next = self.siblings.get(order=next)
            except:
                self._next = None
        return self._next

    @property
    def is_last(self):
        return self.next is None

    def activate(self):
        if self.has_children is True:
            self.activate_children()
            self.status = 2
        else:
            self.status = 3
        self.save()

    def resolve(self, resolution=1, bubble_up=True):
        self.status = 5
        self.resolution = resolution
        self.save()
        if bubble_up:
            if self.parent is not None and (self.resolves_parent or 
                                            self.is_last):
                if self.resolution == 2:
                    bubble_up = False
                    clone = self.parent.clone()
                    clone.activate()
                if not self.is_any_sibling_status(2, 3):
                    self.parent.resolve(self.resolution, bubble_up)
            elif (self.resolution == 1 and
                  not self.is_last and
                  self.next.status_is('new')):
                self.next.activate()
