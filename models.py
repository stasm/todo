from django.db import models
from django.contrib.auth.models import User

from life.models import Locale

from todo.proto.models import Prototype, Actor as ProtoActor
from todo.managers import StatusManager, TaskManager, ProtoManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
from todo.signals import todo_changed
    
from datetime import datetime

class Actor(ProtoActor):
    
    class Meta:
        proxy = True
    
    @property
    def code(self):
        return self.slug

PROJECT_TYPE_CHOICES = (
    (1, 'Product'),
    (2, 'Web'),
    (99, 'Other'),
)
        
class Project(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)
    type = models.PositiveIntegerField(choices=PROJECT_TYPE_CHOICES, default=99)
    
    objects = StatusManager()
    
    def __unicode__(self):
        return self.name
    
    @property
    def code(self):
        return self.slug
        
class Batch(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)
    project = models.ForeignKey(Project, related_name='batches')
    
    objects = StatusManager()
    
    def __unicode__(self):
        return self.name


class Todo(models.Model):
    prototype = models.ForeignKey(Prototype, related_name='instances', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    task = models.ForeignKey('self', related_name='steps', null=True, blank=True)
    owner = models.ForeignKey(Actor, null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    
    # tasks only
    locale = models.ForeignKey(Locale, related_name='tasks', null=True, blank=True)
    bug = models.PositiveIntegerField(null=True, blank=True)
    #move to Bug?
    project = models.ForeignKey(Project, related_name='tasks', null=True, blank=True)
    batch = models.ForeignKey(Batch, related_name='tasks', null=True, blank=True)
    
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES, null=True, blank=True)
    
    _has_children = models.NullBooleanField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last
    
    objects = StatusManager()
    tasks = TaskManager()
    proto = ProtoManager()
    
    _next = None

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return self.summary if not self.locale else "[%s] %s" % (self.locale.code, self.summary)

    def save(self):
        super(Todo, self).save()
        todo_changed.send(sender=self, user=User.objects.get(pk=1), action=self.status)

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
        
    def status_is(self, status_adj):
        return self.get_status_display() == status_adj
        
    def is_next(self):
        return self.status == 3
        
    @models.permalink
    def get_absolute_url(self):
            return ('todo.views.task', [str(self.id)])
    
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
    def is_task(self):
        return self.task is None