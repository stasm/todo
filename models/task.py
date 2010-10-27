from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .project import Project
from .proto import ProtoTask
from .tracker import Tracker
from todo.managers import StatusManager
from todo.workflow import STATUS_CHOICES, RESOLUTION_CHOICES
from todo.signals import status_changed
    
from datetime import datetime

class TaskInProject(models.Model):
    task = models.ForeignKey('Task', related_name="statuses")
    project = models.ForeignKey(Project, related_name="task_statuses")
    status = models.PositiveIntegerField(choices=STATUS_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)

    class Meta:
        app_label = 'todo'
        unique_together = ('task', 'project')

class Task(Todo):
    prototype = models.ForeignKey(ProtoTask, related_name='tasks', null=True,
                                  blank=True)
    parent = models.ForeignKey(Tracker, related_name='tasks', null=True,
                               blank=True)
    summary = models.CharField(max_length=200, blank=True)
    locale = models.ForeignKey(Locale, related_name='tasks', null=True,
                               blank=True)
    projects = models.ManyToManyField(Project, related_name='tasks',
                                      through=TaskInProject)
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)
    # a timestamp reflecting the up-to-date-ness of the Task compared to the 
    # activity in the related bug
    snapshot_ts = models.DateTimeField(null=True, blank=True)
    # a timestamp: when was the last time a Step under this Task was resolved?
    # it is set by a signal callback  (see `todo.models.log_status_change`)
    latest_resolution_ts = models.DateTimeField(null=True, blank=True)

    objects = StatusManager()
    
    class Meta:
        app_label = 'todo'

    def __init__(self, *args, **kwargs):
        """Initialize a Task object.

        The method accepts one additional argument besides the ones defined by
        the model definiton: `suffix`.  If given, it will be appended to the
        parent's `alias` to create the current todo's alias.  This provides
        a breadcrumbs-like functionality.

        Alternatively, you can pass `alias` directly, which will make the
        method ignore the `suffix` and set `self.alias` to the value passed.

        """
        suffix = kwargs.pop('suffix', None)
        parent = kwargs.get('parent', None)
        alias = kwargs.get('alias', None)
        if not alias:
            prefix = parent.alias if parent else None
            bits = [bit for bit in (prefix, suffix) if bit]
            kwargs['alias'] = '-'.join(bits)
        super(Todo, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return self.summary

    def assign_to_projects(self, projects):
        for project in projects:
            TaskInProject.objects.create(task=self, project=project)

    def is_resolved_all(self):
        return not self.statuses.filter(status__lt=5).count()

    @property
    def code(self):
        return str(self.id)

    @models.permalink
    def get_admin_url(self):
        return ('admin:todo_task_change', [self.id])

    def clone(self):
        return self.prototype.spawn(summary=self.summary, parent=self.parent,
                                    locale=self.locale, bug=self.bug)

    def children_all(self):
        """Get the immediate children of the task.
        
        Note the this is different from self.steps which is a manager handling
        all steps under the task, no matter how deep they are in the steps
        hierarchy.

        Backstory:  Tasks do not have the `children` manager, and instead, you
        need to query for Steps with no parent (because only other Steps can be
        Steps' parents).  Since you make an actual query, you get a queryset,
        so the behavior is inconsistent with that of accessing `children` on
        Steps and Tracker (which returns a manager).

        """
        return self.steps.top_level()

    def siblings_all(self):
        """Get a QuerySet with the Task siblings of the current Task.
        
        Returns sibling Tasks only, without Trackers which might happen to be
        at the same level in the hierarchy as the Task.  In order to get the
        sibling Trackers, call Task.parent.children_all.
        
        See `todo.models.base.TodoInterface.siblings_all` for more docs.
 
        """
        return self.parent.tasks.all()

    def next_steps(self):
        "Get the next steps in the task."
        return self.steps.next()

    def resolve(self, user, project, resolution=1):
        "Resolve the task."
        status = self.statuses.get(project=project)
        status.status = 5
        status.resolution = resolution
        status.save()
        status_changed.send(sender=self, user=user, action=5)

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
