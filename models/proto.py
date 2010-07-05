from django.db import models
from django.contrib.contenttypes.models import ContentType

from todo.models import Actor

PROTO_TYPE_CHOICES = (
    (1, 'tracker'),
    (2, 'task'),
    (3, 'step'),
)

class Proto(models.Model):
    """Base prototype model.
    
    All relationships stored in the Nesting model instances work with this
    model. This means that Nestings will give you Proto objects. Use
    Proto.get_related_model to go from Proto to a specific proto model.
    
    """
    summary = models.CharField(max_length=200, blank=True)
    type = models.PositiveIntegerField(choices=PROTO_TYPE_CHOICES)

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def __init__(self, *args, **kwargs):
        super(Proto, self).__init__(*args, **kwargs)
        if self.id is None:
            self.type = self._type

    def __unicode__(self):
        return "[%s] %s" % (self.get_type_display(), self.summary)

    def get_related_model(self):
        """Get the model class that the proto spawns."""

        ct = ContentType.objects.get(app_label="todo", 
                                     model=self.get_type_display())
        return ct.model_class()

    def get_proto_object(self):
        """Move from Proto to Proto{Tracker,Task,Step}"""

        return getattr(self, 'proto%s' % self.get_type_display())

    def _spawn_instance(self, **custom_fields):
        """Create an instance of the model related to the proto."""

        related_model = self.get_related_model()
        accepted_fields = [f.name for f in related_model._meta.fields]
        fields = {}
        # get prototype's attribute values
        proto_fields = [(f, getattr(self, f)) for f in self.inheritable]
        fields.update(proto_fields)
        # remove empty/unknown values from custom_fields
        # and overwrite other attributes
        custom_fields = [(k, v) for k, v in custom_fields.items()
                                if v and k in accepted_fields]
        fields.update(custom_fields)
        return related_model(prototype=self, **fields)

    def _spawn_children(self, **custom_fields):
        """Create children of a todo object."""

        for nesting in self.nestings_where_parent:
            child = nesting.child.get_proto_object()
            if nesting.clone_per_locale is True:
                # to avoid conflicts, locale and locales are deleted
                # from custom_fields and are not passed to children
                # directly
                locale = custom_fields.pop('locale', None)
                locales = custom_fields.pop('locales', [locale])
                for loc in locales:
                    child.spawn(locale=loc, **custom_fields)
            else:
                child.spawn(**custom_fields)

    def spawn(self, **custom_fields):
        """Create an instance of the model related to the proto, with children.
        
        This method creates an instance of the model related to the current
        prototype, e.g. in case of a ProtoTracker, it will create a Tracker.
        It also creates all the children of the newly created Tracker, Task
        or Step (the 'todo' objects).

        The todo objects will be created with properties as set on the
        prototypes and nestings. You can override them by passing custom
        values in the keyword arguments.

        A special iterable `locales` keyword argument can be passed to create
        multiple trees of todo objects, one per locale in `locales`. Only
        todo objects with clone_per_locale set on the corresponding nesting
        will be cloned in this way.

        The method always returns just one, top-level todo object, even if
        more were created as children.

        """
        todo = self._spawn_instance(**custom_fields)
        todo.save()
        custom_fields.update(parent=todo)
        if 'summary' in custom_fields:
            # custom summary should not propagate further down
            del custom_fields['summary']
        self._spawn_children(**custom_fields)
        return todo

class ProtoTracker(Proto):
    """Proto Tracker model.

    This model is used to store prototypes of trackers.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='prototracker')
    inheritable = ('summary',)
    # `_type` is used by Proto.__init__ to set `type` in the DB correctly
    _type = 1

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

class ProtoTask(Proto):
    """Proto Task model.

    This model is used to store prototypes of tasks.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='prototask')
    inheritable = ('summary',)
    _type = 2

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def spawn(self, **custom_fields):
        todo = self._spawn_instance(**custom_fields)
        todo.save()
        custom_fields.update(task=todo)
        if 'summary' in custom_fields:
            # custom summary should not propagate further down
            del custom_fields['summary']
        if 'parent' in custom_fields:
            # `parent` might have been used before to create relationships
            # between Trackers or Trackers/Tasks.
            del custom_fields['parent']
        self._spawn_children(**custom_fields)
        return todo

class ProtoStep(Proto):
    """Proto Step model.

    This model is used to store prototypes of steps.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='protostep')
    owner = models.ForeignKey(Actor, null=True, blank=True)
    is_review = models.BooleanField(default=False)
    inheritable = ('summary', 'owner', 'is_review')
    _type = 3

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

class Nesting(models.Model):
    """Nesting model stores the relationships between Proto objects.

    This models is used to store relationship information between
    two Proto objects. It also provides a way to extend this information
    with extra properties. The properties can be set here so that they're
    not bound to a Proto object, but instead can differ depending on what 
    the parent/child is in the relationship.

    """
    parent = models.ForeignKey(Proto, related_name="nestings_where_parent")
    child = models.ForeignKey(Proto, related_name="nestings_where_child")
    # set for child trackers
    clone_per_locale = models.BooleanField(default=False)
    # set for child steps
    order = models.PositiveIntegerField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False)
    resolves_parent = models.BooleanField(default=False)
    repeat_if_failed = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'todo'
        ordering = ('parent', 'order')
    
    def __unicode__(self):
       return "%s in %s" % (self.child, self.parent)
