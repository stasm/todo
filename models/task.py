from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .project import Project
from .proto import ProtoTask
from .tracker import Tracker
from todo.managers import StatusManager
from todo.workflow import statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES, RESOLUTION_CHOICES
    
from datetime import datetime

class Task(Todo):
    prototype = models.ForeignKey(ProtoTask, related_name='tasks', null=True, blank=True)
    parent = models.ForeignKey(Tracker, related_name='tasks', null=True, blank=True)
    summary = models.CharField(max_length=200, blank=True)
    locale = models.ForeignKey(Locale, related_name='tasks', null=True, blank=True)
    project = models.ForeignKey(Project, related_name='tasks')
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)
    snapshot_ts = models.DateTimeField(null=True, blank=True)

    objects = StatusManager()
    
    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return self.summary

    @property
    def code(self):
        return str(self.id)

    @models.permalink
    def get_absolute_url(self):
        return ('todo.views.task', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/task/%s' % str(self.id)

    def clone(self):
        return self.prototype.spawn(summary=self.summary, parent=self.parent,
                                    locale=self.locale, bug=self.bug)

    @property
    def children(self):
        """Get the immediate children of the task.
        
        Note the this is different from self.steps which is a manager handling
        all steps under the task, no matter how deep they are in the steps
        hierarchy.
        
        """
        return self.steps.top_level()

    def next_steps(self):
       """Get the next steps in the task."""
       return self.steps.next()

    def resolve(self, resolution=1):
        self.status = 5
        self.resolution = resolution
        self.save()

    def get_bug(self):
        return self.bugid or self.alias

    def set_bug(self, val):
        if isinstance(val, int):
            self.bugid = val
        else:
            self.bugid = None
            self.alias = val
    
    bug = property(get_bug, set_bug)

    def is_uptodate(self, bug_last_modified_time):
        if self.snapshot_ts is None:
            return False
        return self.snapshot_ts >= bug_last_modified_time

    def snapshot_ts_iso(self):
        return '%sZ' % self.snapshot_ts.isoformat() if self.snapshot_ts is not None else '0'

    def update_snapshot(self, new_snapshot_ts):
        self.snapshot_ts = new_snapshot_ts
        self.save()

    def update_bugid(self, new_bugid):
        self.bugid = new_bugid
        self.save()
