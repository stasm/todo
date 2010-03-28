from django.db import models
from django.contrib.auth.models import User
from todo.proto.models import Prototype, Nesting

class StatusManager(models.Manager):
    use_for_related_fields = True
    def open(self):
        return self.filter(status__in=(1, 2, 3))
    def new(self):
        return self.filter(status=1)
    def active(self):
        return self.filter(status__in=(2, 3))
    def next(self):
        return self.filter(status=3)
    def on_hold(self):
        return self.filter(status=4)
    def resolved(self):
        return self.filter(status=5)
        
class TaskManager(StatusManager):
    def filter(self, *args, **kwargs):
        return super(TaskManager, self).filter(parent=None, *args, **kwargs)
    def all(self):
        return self.filter()

class ProtoManager(models.Manager):
    inheritable = ['summary', 'owner', 'is_review']
    
    def _create(self, prototype, **custom_fields):
        fields = custom_fields
        if prototype is not None:
            for prop in self.inheritable:
                if not custom_fields.has_key(prop) or custom_fields[prop] is None or custom_fields[prop] == '':
                    fields[prop] = getattr(prototype, prop)
        todo = self.model(prototype=prototype, **fields)
        return todo
    
    def _create_with_children(self, prototype, **custom_fields):
        todo = self._create(prototype, **custom_fields)
        nestings = Nesting.objects.filter(parent=prototype,
                                          child__in=prototype.children.all())
        todo.has_children = True if len(nestings) > 0 else False
        todo.save()
        for nesting in nestings:
            child_fields = {
                'parent': todo,
                'order': nesting.order,
                'is_auto_activated': nesting.is_auto_activated,
                'resolves_parent': nesting.resolves_parent
            }
            self._create_with_children(nesting.child, **child_fields)
        return todo
        
    def create(self, prototype, **custom_fields):
        return self._create_with_children(prototype, **custom_fields)
            