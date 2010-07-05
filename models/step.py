from django.db import models
from django.core.urlresolvers import reverse

from todo.models import Actor, Protostep, Todo, Task
from todo.managers import StatusManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
    
from datetime import datetime

class Step(models.Model, Todo):
    prototype = models.ForeignKey(ProtoStep, related_name='steps', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    task = models.ForeignKey(Task, related_name='steps', null=True, blank=True)
    owner = models.ForeignKey(Actor, null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES, null=True, blank=True)
    
    _has_children = models.NullBooleanField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last

    objects = StatusManager()
    
    _next = None

    class Meta:
        app_label = 'todo'
        ordering = ('order',)

    def __unicode__(self):
        return self.summary

    @models.permalink
    def get_absolute_url(self):
        return ('todo.views.task', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/todo/%s' % str(self.id)

    def get_has_children(self):
        if self._has_children is None:
            self._has_children = len(self.children.all()) > 0
        return self._has_children

    def set_has_children(self, value):
        self._has_children = value

    has_children = property(get_has_children, set_has_children)

    def clone(self):
        return Todo.proto.create(self.prototype, task=self.task, parent=self.parent, order=self.order)

    def resolve(self, resolution=1, cascade=True):
        self.status = 5
        self.resolution = resolution
        self.save()
        if cascade and not self.is_task:
            if self.resolves_parent or self.is_last:
                if self.resolution == 2:
                    cascade = False
                    clone = self.parent.clone()
                    clone.activate()
                if not self.any_sibling_is('active'):
                    self.parent.resolve(self.resolution, cascade)
            elif self.resolution == 1 and self.next.status_is('new'):
                self.next.activate()

    def activate(self):
        if self.has_children:
            self.activate_children()
            self.status = 2
        else:
            self.status = 3
        self.save()

    def activate_children(self):
        auto_activated_children = self.children.filter(is_auto_activated=True)
        if len(auto_activated_children) == 0:
            auto_activated_children = (self.children.get(order=1),)
        for child in auto_activated_children:
            child.activate()

    def any_sibling_is(self, method):
        return bool(getattr(self.parent.children, method)())

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_next(self):
        return self.status == 3

    def is_open(self):
        return self.status != 5

    @property
    def next(self):
        if self._next is None:
            try:
                next = self.order + 1
                self._next = self.parent.children.get(order=next)
            except:
                self._next = None
        return self._next

    @property
    def is_last(self):
        return self.next is None

    @property
    def code(self):
        return str(self.id)
