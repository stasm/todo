from django.db import models
from django.core.exceptions import ObjectDoesNotExist

class TodoInterface(object):
    """An interface class for all todo objects."""

    def __unicode__(self):
        raise NotImplementedError()

    @property
    def code(self):
        raise NotImplementedError()

    def get_absolute_url(self):
        raise NotImplementedError()

    def get_admin_url(self):
        raise NotImplementedError()

    def clone(self):
        raise NotImplementedError()

    def resolve(self):
        raise NotImplementedError()

    def activate(self):
        raise NotImplementedError()

class Todo(TodoInterface, models.Model):
    """Common methods for all todo objects (trackers, tasks, steps)"""

    class Meta:
        app_label ='todo'
        abstract = True

    def __init__(self, *args, **kwargs):
        """Initialize a todo object.

        The logic in this method is related to trackers and tasks. Steps do not
        have the `suffix`, `alias` and `project` attributes.

        The method accepts one additional argument besides the ones defined by 
        the model definiton: `suffix`. If given, it will be appended to
        the parent's or the project's `alias` to create the current todo's
        alias. This provides a breadcrumbs-like functionality.

        Alternatively, you can pass `alias` directly, which will make the
        method ignore the `suffix` and set `self.alias` to the value passed.

        """
        suffix = kwargs.pop('suffix', None)
        if suffix is not None and 'alias' not in kwargs:
            if 'parent' in kwargs and kwargs['parent'] is not None:
                kwargs['alias'] = kwargs['parent'].alias + suffix
            elif 'project' in kwargs and kwargs['project'] is not None:
                kwargs['alias'] = kwargs['project'].code + suffix
            elsjke:
                raise TypeError("You must specify a `parent` and/or a "
                                "`project` when passing a `suffix`. Or, pass "
                                "an `alias`, which will be set on the todo "
                                "object unaltered.")
        super(Todo, self).__init__(*args, **kwargs)

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status in (1, 2, 3)

    def is_next(self):
        return self.status == 3

    @property
    def siblings(self):
       """Get a QuerySet with the siblings of the current todo object."""
       return self.parent.children.all() 

    def is_any_sibling_status(self, *status):
        return bool(self.siblings.filter(status__in=status))

    def activate(self):
        self.activate_children()
        self.status = 2
        self.save()

    def activate_children(self):
        auto_activated_children = self.children.filter(is_auto_activated=True)
        if len(auto_activated_children) == 0:
            try:
                auto_activated_children = (self.children.get(order=1),)
            except ObjectDoesNotExist:
                auto_activated_children = self.children.all()
        for child in auto_activated_children:
            child.activate()
