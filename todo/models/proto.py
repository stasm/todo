# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla todo app.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from django.db import models, reset_queries
from django.contrib.contenttypes.models import ContentType

from .action import CREATED
from .actor import Actor
from todo.workflow import ACTIVE, NEXT
from todo.signals import status_changed

TRACKER_TYPE, TASK_TYPE, STEP_TYPE = range(1,4)

PROTO_TYPE_CHOICES = (
    (TRACKER_TYPE, 'tracker'),
    (TASK_TYPE, 'task'),
    (STEP_TYPE, 'step'),
)

class Proto(models.Model):
    """Base prototype model.

    This model should not be used independently.  You should always create and
    work with ProtoTrackers, ProtoTasks and ProtoSteps instead.
    
    All relationships stored in the Nesting model instances work with this
    model.  This means that Nestings will give you Proto objects.  Use
    Proto.get_related_model to go from Proto to a specific proto model.
    
    """
    summary = models.CharField(max_length=200)
    type = models.PositiveIntegerField(choices=PROTO_TYPE_CHOICES)

    # The type of the Proto object represented by an integer from
    # PROTO_TYPE_CHOICES.  This must be implemented by the child classes
    # inheriting from Proto.  See `Proto.save` for further docs.
    _type = None

    class Meta:
        app_label = 'todo'
        ordering = ('type', 'summary',)

    def save(self, *args, **kwargs):
        """Save a Proto object in the DB.

        If the object does not exist in the DB yet, the value of its `_type`
        property (which is statically defined on the child models) will be
        stored in a DB field called `type`.  This is done so that when a Proto
        object is retrieved from the DB, it knows which of the three prototype
        types it is (ProtoTracker, ProtoTask or ProtoStep).

        This facilitates the workflow related to Nestings.  Since all Nestings
        store relations between Proto objects, accessing nesting.parent and
        nesting.child returns Proto objects.  And since all Proto objects know
        their `type` (it's stored in the DB), it is possible to use
        `get_related_model` to move from the retrived Proto object to the
        corresponding ProtoTracker, ProtoTask or ProtoStep.

        Note that this method will throw an AssertionError if called to create
        a new vanilla Proto object (that does not exist in the DB).  This is on
        purpose, as Proto objects are instead created automatically when you
        create new ProtoTrackers, ProtoTasks and ProtoSteps.

        """
        if self.id is None:
            # the object does not exist in the DB yet
            # make sure the `_type` property is defined
            assert self._type is not None, '_type must not be None'
            # store the type in the DB
            self.type = self._type
        super(Proto, self).save(*args, **kwargs)

    def __unicode__(self):
        return "[%s] %s" % (self.get_type_display(), self.summary)

    def get_related_model(self):
        "Get the model class that the proto spawns."

        from todo.models import Tracker, Task, Step
        if self.type == TRACKER_TYPE:
            return Tracker
        elif self.type == TASK_TYPE:
            return Task
        elif self.type == STEP_TYPE:
            return Step
        else:
            raise TypeError('The Prototype object has an unknown type.')

    def get_proto_object(self):
        "Move from Proto instance to Proto{Tracker,Task,Step} instance"

        return getattr(self, 'proto%s' % self.get_type_display())

    def _spawn_instance(self, user, activate, **custom_fields):
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
        # store the string representation of the todo as its property before 
        # it is saved, in order to avoid a query made by todo.get_repr
        todo.repr = todo.format_repr(**fields)
        if self.type == STEP_TYPE:
            if activate and todo.should_be_activated():
                # a Step can only be related to a single Project (or, more 
                # often, to no projects at all), so its status is stored 
                # directly as a property.
                todo.status = ACTIVE
            todo.save()
        else:
            # save it so that it has an ID
            todo.save()
            # in order to create relations between Trackers/Tasks and Projects, 
            # create required {Tracker,Task}InProject objects handling the 
            # many-to-many relation; set the status to 'active' is requested.
            todo.assign_to_projects(projects,
                                    status=ACTIVE if activate else None)
        status_changed.send(sender=todo, user=user, flag=CREATED)
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

    def _spawn_children(self, user, activate, cloning_allowed,
                        **custom_fields):
        "Create children of the todo object."

        children = []
        for nesting in self.nestings_where_parent.select_related('child'):
            child = nesting.child.get_proto_object()
            # steps inside task/steps inherit the following
            # properties from the nesting, not the proto itself
            for prop in ('order', 'is_auto_activated'):
                custom_fields.update({prop: getattr(nesting, prop)})
            # since `spawn` and `spawn_per_*` might delete keys, 
            # let's not do that on the original `custom_fields` which 
            # will be used by other nestings in the loop
            fields = custom_fields.copy()
            if activate and child.type == STEP_TYPE:
                activate = nesting.should_be_activated()
            if cloning_allowed['locale'] and child.clone_per_locale:
                spawned = child.spawn_per_locale(user, activate=activate,
                                                 **fields)
            elif cloning_allowed['project'] and child.clone_per_project:
                spawned = child.spawn_per_project(user, activate=activate,
                                                  **fields)
            else:
                # a tuple because it needs to be iterable in the next line
                spawned = (child.spawn(user, activate=activate,
                                       cloning_allowed=cloning_allowed,
                                       **fields),)
            children.extend(spawned)
        return children

    def spawn(self, user, activate=True, cloning_allowed=None,
              **custom_fields):
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
        todo = self._spawn_instance(user, activate=activate, **custom_fields)
        # remove fields that should not propagate onto the children
        custom_fields = self._prepare_fields_for_children(custom_fields, todo)
        children = self._spawn_children(user, activate=activate,
                                        cloning_allowed=cloning_allowed,
                                        **custom_fields)
        if (self.type == STEP_TYPE and activate and
            todo.status == ACTIVE and not children):
            # if a Step has no children, mark it as 'next' instead of 'active'
            todo.status = NEXT
            # todo was already saved in _spawn_instance, so we don't need 
            # Django to check (with an extra SELECT) if it needs to make an 
            # INSERT or an UPDATE here. See <http://docs.djangoproject.com/en/ 
            # 1.1/ref/models/instances/#how-django-knows-to-update-vs-insert>.
            todo.save(force_update=True)
        return todo

    def spawn_per_locale(self, user, activate=True, **fields):
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
        # to avoid conflicts, locale and locales are deleted from custom_fields 
        # and are not passed to children directly (we don't want to clone more 
        # then once in a single tracker tree).
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
            # if settings.DEBUG is True, clear django.db.connection.queries 
            # before a per-locale tree is spawned; spawning generates huge 
            # amount of queries and keeping track of all of them for debugging 
            # purposes is too much for Python
            reset_queries()
            yield self.spawn(user, activate=activate, locale=loc,
                             cloning_allowed=cloning_allowed, **fields)

    def spawn_per_project(self, user, activate=True, **fields):
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
            yield self.spawn(user, activate=activate, project=project,
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
    _type = TRACKER_TYPE

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
    _type = TASK_TYPE

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
    _type = STEP_TYPE

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

    def should_be_activated(self):
        return self.is_auto_activated or self.order == 1
