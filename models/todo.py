class Todo(object):
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

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status != 5
