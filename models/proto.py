from django.db import models
from django.contrib.contenttypes.models import ContentType

from .actor import Actor
from todo.signals import status_changed

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
    summary = models.CharField(max_length=200)
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
        "Get the model class that the proto spawns."

        ct = ContentType.objects.get(app_label="todo", 
                                     model=self.get_type_display())
        return ct.model_class()

    def get_proto_object(self):
        "Move from Proto instance to Proto{Tracker,Task,Step} instance"

        return getattr(self, 'proto%s' % self.get_type_display())

    def _spawn_instance(self, **custom_fields):
        "Create an instance of the model related to the proto."

        related_model = self.get_related_model()
        # fields that are accepted by the spawned object
        accepted_fields = [f.name for f in related_model._meta.fields]
        if self.type in (1, 2):
            # for trackers and tasks. need to add this because the field is
            # called `alias`, but you can pass a `suffix` which will be
            # appended to the parent's `alias`.
            accepted_fields.append('suffix')
            projects = custom_fields.get('projects', None)
        else:
            # steps don't belong to projects. Their parent tasks do.
            projects = None
        # remove empty/unknown values from custom_fields and overwrite other
        # attributes
        custom_fields = [(k, v) for k, v in custom_fields.items()
                                if v and k in accepted_fields]
        # fields (with values) which will be inherited by the spawned object
        fields = dict([(f, getattr(self, f)) for f in self.inheritable])
        # custom fields override fields from the proto
        fields.update(custom_fields)
        todo = related_model(prototype=self, **fields)
        todo.save()
        # in order to create relations between Trackers/Tasks and Project,
        # create required {Tracker,Task}InProject objects handling the
        # many-to-many relation.
        if projects:
            todo.assign_to_projects(projects)
        return todo

    def _spawn_children(self, user, cloning_allowed, **custom_fields):
        "Create children of the todo object."

        for nesting in self.nestings_where_parent.all():
            child = nesting.child.get_proto_object()
            # steps inside task/steps inherit the following
            # properties from the nesting, not the proto itself
            for prop in ('order', 'is_auto_activated'):
                custom_fields.update({prop: getattr(nesting, prop)})
            # since `spawn` and `spawn_per_locale` might delete keys, 
            # let's not do that on the original `custom_fields` which 
            # will be used by other nestings in the loop
            fields = custom_fields.copy()
            if cloning_allowed and child.clone_per_locale:
                # `spawn_per_locale` is a generator
                list(child.spawn_per_locale(user, **fields))
            else:
                child.spawn(user, cloning_allowed, **fields)

    def spawn(self, user, cloning_allowed=True, **custom_fields):
        """Create an instance of the model related to the proto, with children.
        
        This method creates an instance of the model related to the current
        prototype, e.g. in case of a ProtoTracker, it will create a Tracker.
        It also creates all the children of the newly created Tracker, Task
        or Step (the 'todo' objects).

        The todo objects will be created with properties as set on the
        prototypes and nestings. You can override them by passing custom
        values in the keyword arguments.

        A `project` keyword argument is required when spawning trackers or
        tasks. It must be an instance of todo.models.Project. The created todo 
        objects will be related to the project passed.

        A special iterable `locales` keyword argument can be passed to create
        multiple trees of todo objects, one per locale in `locales`. Only
        todo objects with clone_per_locale set to True will be cloned in this
        way.

        The method always returns just one, top-level todo object, even if
        more were created as children.

        """
        if self.type in (1, 2) and 'projects' not in custom_fields:
            raise TypeError("Pass projects to spawn trackers and tasks.")
        todo = self._spawn_instance(**custom_fields)
        todo.save()
        status_changed.send(sender=todo, user=user, action=1)
        if self.type in (1, 3):
            # trackers and steps
            to_be_removed = self.inheritable
            custom_fields.update(parent=todo)
        else:
            # tasks
            # Steps are related to Tasks via the `task` property which is set 
            # above, and the top-level steps have the `parent` property set 
            # to None. Here, we're removing `parent` to make sure the child
            # steps are `parent`-less. (`parent` might have been used before
            # to create relationships between Trackers or Trackers/Tasks). 
            to_be_removed = self.inheritable + ('parent',)
            custom_fields.update(task=todo)
        for prop in to_be_removed:
            # these properties are inheritable by the current todo object,
            # but not by its children. they should not propagate further down.
            if prop in custom_fields:
                del custom_fields[prop]
        self._spawn_children(user, cloning_allowed, **custom_fields)
        return todo

    def spawn_per_locale(self, user, **fields):
        """Create multiple todo objects from a single prototype per locale.

        If `locales` iterable is passed in `fields`, the prototype will be used
        to create multiple todo objects, one per locale given.

        This method is a wrapper around a regular `spawn`. It loops over the
        list of locales passed in as a keyword argument, adjusts the alias
        suffix so that it ends with `-ab` (where `ab` is a locale's code) and
        calls `spawn`.

        """
        # to avoid conflicts, locale and locales are deleted
        # from custom_fields and are not passed to children
        # directly (we don't want to clone more then once in a single
        # tracker tree).
        locale = fields.pop('locale', None)
        locales = fields.pop('locales', None)
        if not locales:
            # we could have done locales = fields.pop('locales', [locale])
            # above, but this wouldn't have worked when fields['locales'] is
            # an empty list.
            locales = [locale]
        alias = fields.pop('alias', None)
        suffix = fields.pop('suffix', None)
        if not suffix:
            # if suffix is None or empty, use prototype's suffix
            suffix = self.suffix
        for loc in locales:
            if loc:
                # the suffix part will always run, so that if `suffix` is None,
                # the resulting fields['suffix'] contains at least the loc.code
                bits = [bit for bit in (suffix, loc.code) if bit]
                fields['suffix'] = '-'.join(bits)
                if alias:
                    # the alias part should only run if the `alias` was passed
                    # in the fields, which means that the user intends to make
                    # use of it (it will override the suffix)
                    fields['alias'] = '-'.join((alias, loc.code))
            yield self.spawn(user, locale=loc, cloning_allowed=False,
                             **fields)

class ProtoTracker(Proto):
    """Proto Tracker model.

    This model is used to store prototypes of trackers.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='prototracker')
    clone_per_locale = models.BooleanField(default=True, 
                                           help_text="If False, the tracker "
                                           "will never be cloned orthogonally "
                                           "per locale if none of its parents "
                                           "has been cloned yet. Leaving this "
                                           "as True should be OK for 90% of "
                                           "cases.")
    suffix = models.SlugField(max_length=8, blank=True)
    # tuple of prototype's properties that can be inherited by a spawned object
    inheritable = ('summary', 'suffix')
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
    suffix = models.SlugField(max_length=8, blank=True)
    # this is always True so no need to store it in the DB
    clone_per_locale = True
    inheritable = ('summary', 'suffix')
    _type = 2

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

class ProtoStep(Proto):
    """Proto Step model.

    This model is used to store prototypes of steps.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='protostep')
    owner = models.ForeignKey(Actor, null=True, blank=True)
    is_review = models.BooleanField(default=False)
    allowed_time = models.PositiveSmallIntegerField(default=3,
                                        verbose_name="Allowed time (in days)",
                                        help_text="Time the owner has to "
                                                  "complete the step.")
    # this is always False so no need to store in the DB
    clone_per_locale = False
    inheritable = ('summary', 'owner', 'is_review', 'allowed_time')
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
    # set for child steps
    order = models.PositiveIntegerField(null=True, blank=True)
    is_auto_activated = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'todo'
        ordering = ('parent', 'order')
    
    def __unicode__(self):
       return "%s in %s" % (self.child, self.parent)
