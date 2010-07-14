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

class Todo(TodoInterface):
    """Common methods for all todo objects (trackers, tasks, steps)"""

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status != 5

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
