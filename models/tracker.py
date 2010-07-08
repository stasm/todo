from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .proto import ProtoTracker
from todo.managers import StatusManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES

class Tracker(models.Model, Todo):
    prototype = models.ForeignKey(ProtoTracker, related_name='trackers', null=True, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True)
    summary = models.CharField(max_length=200)
    locale = models.ForeignKey(Locale, related_name='trackers', null=True, blank=True)
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)

    objects = StatusManager()

    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        if self.locale:
            return "[%s] %s" % (self.locale.code, self.summary)
        return self.summary
    
    @property
    def code(self):
        return str(self.id)
    
    @models.permalink
    def get_absolute_url(self):
        return ('todo_project_dashboard', (self.project.slug,))

    def get_admin_url(self):
        return '/admin/todo/todo/%s' % str(self.id)

    def clone(self):
        return self.prototype.spawn(parent=self.parent)

    def resolve(self, resolution=1):
        self.status = 5
        self.resolution = resolution
        self.save()

    def activate(self):
        self.activate_children()
        self.status = 2
        self.save()

    def activate_children(self):
        for child in self.children.all():
            child.activate()

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status != 5
