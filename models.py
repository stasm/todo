from django.db import models
from django.contrib.auth.models import Group, User

from todo.proto.models import Prototype
from todo.managers import TodoManager, TaskManager, ProtoManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
from todo.signals import todo_changed
    
from datetime import datetime

class Todo(models.Model):
    prototype = models.ForeignKey(Prototype, related_name='instances', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    owner = models.ForeignKey(Group, null=True, blank=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES, null=True, blank=True)
    
    is_auto_activated = models.BooleanField(default=False) #set on first
    is_review = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False) #set on last
    repeat_if_failed = models.BooleanField(default=False) #set on review action's parent
    
    objects = TodoManager()
    tasks = TaskManager()
    proto = ProtoManager()

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return "%s" % (self.summary,) 

    def save(self):
        super(Todo, self).save()
        todo_changed.send(sender=self, user=User.objects.get(pk=1), action=self.status)
        
    def resolve(self, resolution=1):
        self.status = 4
        self.resolution = resolution
        self.save()
        if self.resolves_parent or self.is_last:
            self.parent.resolve(self.resolution)
        elif self.repeat_if_failed:
            Todo.proto.create(prototype=self.prototype, parent=self.parent, order=self.order)
        else:
            self.next.activate()

    def is_self_or_ancestor(self, attr, value):
        if getattr(self, attr) == value:
            return True
        elif self.parent is not None:
            return self.parent.is_self_or_ancestor(attr, value)
        else:
            return False
            
    def activate(self):
        self.status = 2
        self.save()
        self.activate_children()

    def activate_children(self):
        auto_activated_children = self.children.filter(is_auto_activated=True)
        if len(auto_activated_children) == 0:
            auto_activated_children = (self.children.get(order=1),)
        for child in auto_activated_children:
            child.status = 2
            child.save()

    def children_of_type(self, type_int):
        return self.children.filter(type=type_int)

    @property        
    def siblings(self):
        siblings = []
        for todo in self.parent.children.exclude(pk=self.id):
            siblings.append(todo)
        return siblings        

    @property
    def next(self):
        next = self.order + 1
        try:
            return self.parent.children.get(order=next)
        except:
            return None

    @property
    def is_last(self):
        return self.next is None