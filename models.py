from django.db import models
from django.contrib.auth.models import Group, User

from life.models import Locale

from todo.proto.models import Prototype
from todo.managers import StatusManager, TaskManager, ProtoManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
from todo.signals import todo_changed
    
from datetime import datetime

class Project(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    
    objects = StatusManager()
    
    def __unicode__(self):
        return "%s" % (self.name,)

class Todo(models.Model):
    prototype = models.ForeignKey(Prototype, related_name='instances', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    owner = models.ForeignKey(Group, null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    
    # task-only
    locale = models.ForeignKey(Locale, related_name='todos', null=True, blank=True)
    bug = models.PositiveIntegerField(null=True, blank=True)
    project = models.ForeignKey(Project, related_name='todos', null=True, blank=True)
    
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES, null=True, blank=True)
    
    has_children = models.BooleanField()
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
        
    def clone(self):
        return Todo.proto.create(self.prototype, parent=self.parent, order=self.order)
        
    def resolve(self, resolution=1, bubble_up=True):
        self.status = 4
        self.resolution = resolution
        self.save()
        if bubble_up and not self.is_task:
            if self.resolves_parent or self.is_last:
                if self.resolution == 2:
                    bubble_up = False
                    clone = self.parent.clone()
                    clone.activate()
                self.parent.resolve(self.resolution, bubble_up)
            elif self.resolution == 1 and self.next.status_is('new'):
                self.next.activate()
            
    def activate(self):
        self.status = 2
        self.save()
        if self.has_children:
            self.activate_children()

    def activate_children(self):
        auto_activated_children = self.children.filter(is_auto_activated=True)
        if len(auto_activated_children) == 0:
            auto_activated_children = (self.children.get(order=1),)
        for child in auto_activated_children:
            child.activate()
        
    def is_next_action(self):
        return self.status == 2 and not self.has_children 
        
    def status_is(self, status_adj):
        return self.get_status_display() == status_adj   

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
        return self.parent is None