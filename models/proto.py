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
        # models can define additional accepted fields (e.g. 'suffix')
        accepted_fields += related_model.extra_fields
        # remove projects from custom_fields since related_model.__init__ 
        # (regardless of which model it stands for) does not accept them as
        # argument; store the value for later use, though.
        projects = custom_fields.pop('projects', None)
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
        if projects:
            # in order to create relations between Trackers/Tasks and Project,
            # create required {Tracker,Task}InProject objects handling the
            # many-to-many relation.
            todo.assign_to_projects(projects)
        return todo

    def _prepare_fields_for_children(self, custom_fields, todo):
        """Filter given fields to be suitable for spawning todo's children.

        This method prepares the custom fields given by the user so that the
        children todo items can be spawned properly. It will remove invalid
        fields and make sure that the children are created with proper
        relations to their parents (in other words, it will set the `parent` or
        `task` arguments correctly).

        Arguments:
            todo -- the todo object that was just spawned using this prototype
            custom_fields -- a dict of user-passed fields that will override
                             prototype's values

        Returns:
            a custom_fields dict ready to be used to spawn tracker's children.

        """
        raise NotImplementedError()

    def _remove_fields(self, custom_fields, to_be_removed):
        "Remove given keys from the custom_fields dict."
        for prop in to_be_removed:
            if prop in custom_fields:
                del custom_fields[prop]
        return custom_fields

    def _spawn_children(self, user, cloning_allowed, **custom_fields):
        "Create children of the todo object."

        for nesting in self.nestings_where_parent.all():
            child = nesting.child.get_proto_object()
            # steps inside task/steps inherit the following
            # properties from the nesting, not the proto itself
            for prop in ('order', 'is_auto_activated'):
                custom_fields.update({prop: getattr(nesting, prop)})
            # since `spawn` and `spawn_per_*` might delete keys, 
            # let's not do that on the original `custom_fields` which 
            # will be used by other nestings in the loop
            fields = custom_fields.copy()
            if cloning_allowed['locale'] and child.clone_per_locale:
                # `spawn_per_locale` returns an iterator
                list(child.spawn_per_locale(user, **fields))
            elif cloning_allowed['project'] and child.clone_per_project:
                # `spawn_per_project` returns an iterator
                list(child.spawn_per_project(user, **fields))
            else:
                child.spawn(user, cloning_allowed, **fields)

    def spawn(self, user, cloning_allowed=None, **custom_fields):
        """Create an instance of the model related to the proto, with children.
        
        This method creates an instance of the model related to the current
        prototype, e.g. in case of a ProtoTracker, it will create a Tracker.
        It also creates all the children of the newly created Tracker, Task
        or Step (the 'todo' objects).

        The todo objects will be created with properties as set on the
        prototypes and nestings. You can override them by passing custom
        values in the keyword arguments.

        A `projects` keyword argument is the only required argument. It must be
        a list of todo.models.Project instances. The created todo objects will
        be related to the projects passed.

        A special iterable `locales` keyword argument can be passed to create
        multiple trees of todo objects, one per locale in `locales`. Only
        todo objects with clone_per_locale set to True will be cloned in this
        way.

        The method always returns just one, top-level todo object, even if
        more were created as children.

        """
        # `projects` is the only required argument (the values for all other
        # can be inherited from the prototype)
        if 'projects' not in custom_fields or not custom_fields['projects']:
            raise TypeError("Pass projects to spawn todos.")
        if cloning_allowed is None:
            cloning_allowed = {
                'locale': True,
                'project': True,
            }
        todo = self._spawn_instance(**custom_fields)
        todo.save()
        status_changed.send(sender=todo, user=user, action=1)
        # remove fields that should not propagate onto the children
        custom_fields = self._prepare_fields_for_children(custom_fields, todo)
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
        cloning_allowed = {
            'locale': False,
            'project': True,
        }
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
        # Normally, the whole suffix/alias mechanic is done by the
        # `_spawn_instance` method. If neither `suffix` nor `alias` are passed
        # to the method, the suffix from the prototype will be used. Here,
        # however, we want to modify this behavior so that the resulting
        # aliases contain locale codes (e.g. "foo" becomes "foo-pl" for the
        # Polish locale). In order to achieve this, we will always pass
        # a (amended) `suffix` argument to `_spawn_instance`. If original
        # `suffix` was empty, the prototype's suffix will be passed, so that
        # the behavior remains consistent.
        parent = fields.get('parent', None)
        alias = fields.get('alias', None)
        suffix = fields.get('suffix', None)
        if not suffix:
            # if suffix is not given explicitly, use prototype's suffix
            suffix = self.suffix
        for loc in locales:
            # loc might be None (see above)
            if loc and (not parent or not parent.locale):
                # only executed if there's no parent or if the parent doesn't
                # have a locale set. If it does, we want to use its alias
                # verbatim, as it probably already contains the locale code
                # (and if it doesn't, that's most likely on purpose).
                #
                # the suffix part will always run, so that if `suffix` is None,
                # the resulting fields['suffix'] contains at least the loc.code
                bits = [bit for bit in (suffix, loc.code) if bit]
                fields['suffix'] = '-'.join(bits)
                if alias:
                    # the alias part should only run if the `alias` was passed
                    # in the fields, which means that the user intends to make
                    # use of it (it will override the suffix)
                    fields['alias'] = '-'.join((alias, loc.code))
            yield self.spawn(user, locale=loc, cloning_allowed=cloning_allowed,
                             **fields)

    def spawn_per_project(self, user, **fields):
        """Create multiple todo objects from a single prototype per project.

        This method should only be used for steps (it will have no effect in
        used on other models).

        """
        cloning_allowed = {
            'locale': False,
            'project': False,
        }
        projects = fields.get('projects', None)
        if not projects:
            projects = [None]
        for project in projects:
            yield self.spawn(user, project=project, 
                             cloning_allowed=cloning_allowed, **fields)
        
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
    # this is always False so no need to store in the DB
    clone_per_project = False
    suffix = models.SlugField(max_length=8, blank=True)
    # tuple of prototype's properties that can be inherited by a spawned object
    inheritable = ('summary', 'suffix')
    # `_type` is used by Proto.__init__ to set `type` in the DB correctly
    _type = 1

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def _prepare_fields_for_children(self, custom_fields, todo):
        """Filter custom_fields to be suitable for spawning tracker's children.

        See the docs at Proto._prepare_fields_for_children.

        """
        custom_fields.update(parent=todo)
        to_be_removed = self.inheritable + ('alias',)
        return self._remove_fields(custom_fields, to_be_removed)

class ProtoTask(Proto):
    """Proto Task model.

    This model is used to store prototypes of tasks.

    """
    proto = models.OneToOneField(Proto, parent_link=True,
                                 related_name='prototask')
    suffix = models.SlugField(max_length=8, blank=True)
    # this is always True so no need to store it in the DB
    clone_per_locale = True
    # this is always False so no need to store in the DB
    clone_per_project = False
    inheritable = ('summary', 'suffix')
    _type = 2

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def _prepare_fields_for_children(self, custom_fields, todo):
        """Filter custom_fields to be suitable for spawning task's children.

        See the docs at Proto._prepare_fields_for_children.

        """
        # Child steps are related to Tasks via the `task` property and the
        # top-level steps have the `parent` property set to None. 
        custom_fields.update(task=todo)
        # Here, we're removing `parent` to make sure the child steps are
        # `parent`-less. (`parent` might have been used before to create
        # relationships between Trackers or Trackers/Tasks). 
        to_be_removed = self.inheritable + ('alias', 'parent')
        return self._remove_fields(custom_fields, to_be_removed)

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
    clone_per_project = models.BooleanField(default=False, 
                                            help_text="If True and the task "
                                            "this step is under belongs to "
                                            "multiple projects, a copy of "
                                            "this protostep will be spawned "
                                            "for every project. Works best "
                                            "if the protostep is inside "
                                            "another, grouping protostep.")
    # this is always False so no need to store in the DB
    clone_per_locale = False
    inheritable = ('summary', 'owner', 'is_review', 'allowed_time')
    _type = 3

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def _prepare_fields_for_children(self, custom_fields, todo):
        """Filter custom_fields to be suitable for spawning step's children.

        See the docs at Proto._prepare_fields_for_children.

        """
        custom_fields.update(parent=todo)
        # we'll want to remove `project` if it exists, because we only need it
        # for the step that has `clone_per_project` set to True, not its
        # children
        to_be_removed = self.inheritable + ('alias', 'project')
        return self._remove_fields(custom_fields, to_be_removed)

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
