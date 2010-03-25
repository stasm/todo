from django.db import models
from django.contrib.auth.models import User
from todo.proto.models import Prototype, Nesting

class TodoManager(models.Manager):
    def get_tasks(self):
        return self.filter(parent=None)
    def get_open_tasks(self):
        return self.get_tasks().filter(status__in=(1, 2))


class ProtoManager(models.Manager):
    iterable = ['summary', 'owner', 'is_review']
    
    def _create(self, prototype, **custom_fields):
        fields = custom_fields
        if prototype is not None:
            for prop in self.iterable:
                if not custom_fields.has_key(prop) or custom_fields[prop] is None or custom_fields[prop] == '':
                    fields[prop] = getattr(prototype, prop)
        todo = self.model(prototype=prototype, **fields)
        todo.save()
        return todo
    
    def _create_with_children(self, prototype, **custom_fields):
        todo = self._create(prototype, **custom_fields)
        nestings = Nesting.objects.filter(parent=prototype,
                                          child__in=prototype.sub_steps.all())
        for nesting in nestings:
            child_fields = {
                'parent': todo,
                'order': nesting.order,
                'is_auto_activated': nesting.is_auto_activated,
                'resolves_parent': nesting.resolves_parent,
                'repeat_if_failed': nesting.repeat_if_failed,
            }
            self._create_with_children(nesting.child, **child_fields)

        return todo
        
    def create(self, prototype, **custom_fields):
        if not isinstance(prototype, Prototype):
            raise Exception("Specified object must be a Prototype.")
        return self._create_with_children(prototype, **custom_fields)
            