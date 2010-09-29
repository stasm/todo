from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .project import Project
from .proto import ProtoTracker
from todo.managers import StatusManager
from todo.workflow import STATUS_CHOICES, RESOLUTION_CHOICES
from todo.signals import status_changed

class TrackerInProject(models.Model):
    tracker = models.ForeignKey('Tracker', related_name="statuses")
    project = models.ForeignKey(Project, related_name="tracker_statuses")
    status = models.PositiveIntegerField(choices=STATUS_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)

    class Meta:
        app_label = 'todo'
        unique_together = ('tracker', 'project')

class Tracker(Todo):
    prototype = models.ForeignKey(ProtoTracker, related_name='trackers',
                                  null=True, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True,
                               blank=True)
    summary = models.CharField(max_length=200)
    locale = models.ForeignKey(Locale, related_name='trackers', null=True,
                               blank=True)
    projects = models.ManyToManyField(Project, related_name='trackers',
                                      through=TrackerInProject)
    status = models.PositiveIntegerField(choices=STATUS_CHOICES, default=1)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)

    objects = StatusManager()

    class Meta:
        app_label = 'todo'

    def __unicode__(self):
        return self.summary

    def assign_to_projects(self, projects):
        for project in projects:
            TrackerInProject.objects.create(tracker=self, project=project)
    
    @property
    def code(self):
        return str(self.id)
    
    @models.permalink
    def get_admin_url(self):
        return ('admin:todo_tracker_change', [self.id])

    def is_generic(self):
        return self.prototype is None

    def clone(self):
        return self.prototype.spawn(summary=self.summary, parent=self.parent,
                                    locale=self.locale)

    def children_all(self):
        "Get child trackers of the tracker."
        return self.children.all()

    def siblings_all(self):
        """Get a QuerySet with the siblings of the tracker.
        
        See `todo.models.base.TodoInterface.siblings_all` for more docs.
 
        """
        if self.parent is None:
            return Tracker.objects.top_level()
        else:
            return super(Tracker, self).siblings_all()

    def activate_children(self, user):
        "Activate child trackers and tasks."
        for child in self.children_all():
            child.activate(user)
        for task in self.tasks.all():
            task.activate(user)

    def resolve(self, user, resolution=1):
        self.status = 5
        self.resolution = resolution
        self.save()
        status_changed.send(sender=self, user=user, action=self.status)

    def get_bug(self):
        return self.bugid or self.alias

    def set_bug(self, val):
        if isinstance(val, int):
            self.bugid = val
        else:
            self.bugid = None
            self.alias = val
    
    bug = property(get_bug, set_bug)
