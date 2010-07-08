from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .proto import ProtoTask
from .tracker import Tracker
from todo.managers import StatusManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
    
from datetime import datetime

class Task(models.Model, Todo):
    prototype = models.ForeignKey(ProtoTask, related_name='tasks', null=True, blank=True)
    parent = models.ForeignKey(Tracker, related_name='tasks', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    locale = models.ForeignKey(Locale, related_name='tasks', null=True, blank=True)
    bug = models.PositiveIntegerField(null=True, blank=True)
    snapshot_ts = models.DateTimeField(null=True, blank=True)
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)

    objects = StatusManager()
    
    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return self.summary if not self.locale else "[%s] %s" % (self.locale.code, self.summary)

    @property
    def code(self):
        return str(self.id)

    @models.permalink
    def get_absolute_url(self):
        return ('todo.views.task', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/todo/%s' % str(self.id)

    def clone(self):
        return self.prototype.spawn(task=self.task, parent=self.parent,
                                    order=self.order)

    def resolve(self, resolution=1):
        self.status = 5
        self.resolution = resolution
        self.save()

    def activate(self):
        self.activate_children()
        self.status = 2
        self.save()

    def activate_children(self):
        auto_activated_children = self.children.filter(is_auto_activated=True)
        if len(auto_activated_children) == 0:
            auto_activated_children = (self.children.get(order=1),)
        for child in auto_activated_children:
            child.activate()

    def is_uptodate(self, bug_last_modified_time):
        if self.snapshot_ts is None:
            return False
        return self.snapshot_ts >= bug_last_modified_time

    def snapshot_ts_iso(self):
        return '%sZ' % self.snapshot_ts.isoformat() if self.snapshot_ts is not None else '0'

    def update_snapshot(self, new_snapshot_ts):
        self.snapshot_ts = new_snapshot_ts
        self.save()
