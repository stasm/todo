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
    def _create(self, prototype, **custom_fields):
        fields = {}
        if prototype is not None:
            for f in self.model._meta.fields:
                if f.name == 'id':
                    continue
                if custom_fields.has_key(f.name) and custom_fields[f.name]:
                    fields[f.name] = custom_fields[f.name]
                else:
                    try:
                        fields[f.name] = getattr(prototype, f.name)
                    except AttributeError:
                        pass
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
                'task': custom_fields['task'] if custom_fields.has_key('task') else todo,
                'order': nesting.order,
                'is_auto_activated': nesting.is_auto_activated,
                'resolves_parent': nesting.resolves_parent
            }
            self._create_with_children(nesting.child, **child_fields)
        return todo
        
    def create(self, prototype, **custom_fields):
        return self._create_with_children(prototype, **custom_fields)
            