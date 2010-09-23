from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .project import Project
from .proto import ProtoTask
from .tracker import Tracker
from todo.managers import StatusManager
from todo.workflow import (statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES,
                           RESOLUTION_CHOICES)
    
from datetime import datetime

class Task(Todo):
    prototype = models.ForeignKey(ProtoTask, related_name='tasks', null=True,
                                  blank=True)
    parent = models.ForeignKey(Tracker, related_name='tasks', null=True,
                               blank=True)
    summary = models.CharField(max_length=200, blank=True)
    locale = models.ForeignKey(Locale, related_name='tasks', null=True,
                               blank=True)
    project = models.ForeignKey(Project, related_name='tasks')
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)
    # a timestamp reflecting the up-to-date-ness of the Task compared to the 
    # activity in the related bug
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
        # FIXME shouldn't point to a demo view
        return ('todo.views.demo.task', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/task/%s' % str(self.id)

    def clone(self):
        return self.prototype.spawn(summary=self.summary, parent=self.parent,
                                    locale=self.locale, bug=self.bug)

    def children_all(self):
        """Get the immediate children of the task.
        
        Note the this is different from self.steps which is a manager handling
        all steps under the task, no matter how deep they are in the steps
        hierarchy.

        See todo.models.base.Todo for more docs.

        """
        return self.steps.top_level()

    def siblings_all(self):
       """Get a QuerySet with the Task siblings of the current Task.
       
       Returns sibling Tasks only, without Trackers which happen to be at the
       same level in the hierarchy as the Task.  In order to get the sibling
       Trackers, call Task.parent.children_all.

       """
       return self.parent.tasks.all()

    def next_steps(self):
       "Get the next steps in the task."
       return self.steps.next()

    def resolve(self, resolution=1):
        "Resolve the task."
        self.status = 5
        self.resolution = resolution
        self.save()

    def get_bug(self):
        return self.bugid or self.alias

    def set_bug(self, val):
        "Set the `bugid` or `alias` depending on the type of the value passed."
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
        if self.snapshot_ts is not None:
            return '%sZ' % self.snapshot_ts.isoformat()
        return '0'
