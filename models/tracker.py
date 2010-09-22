from django.db import models
from django.core.urlresolvers import reverse

from life.models import Locale

from .base import Todo
from .project import Project
from .proto import ProtoTracker
from todo.managers import StatusManager
from todo.workflow import (statuses, STATUS_ADJ_CHOICES, STATUS_VERB_CHOICES,
                           RESOLUTION_CHOICES)

class Tracker(Todo):
    prototype = models.ForeignKey(ProtoTracker, related_name='trackers',
                                  null=True, blank=True)
    parent = models.ForeignKey('self', related_name='children', null=True,
                               blank=True)
    summary = models.CharField(max_length=200)
    locale = models.ForeignKey(Locale, related_name='trackers', null=True,
                               blank=True)
    project = models.ForeignKey(Project, related_name='trackers')
    status = models.PositiveIntegerField(choices=STATUS_ADJ_CHOICES, default=2)
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)

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
        return ('todo.views.demo.tracker', [str(self.id)])

    def get_admin_url(self):
        return '/admin/todo/tracker/%s' % str(self.id)

    def clone(self):
        return self.prototype.spawn(summary=self.summary, parent=self.parent,
                                    locale=self.locale)

    def siblings_all(self):
       if self.parent is None:
           return Tracker.objects.top_level()
       else:
           return super(Tracker, self).siblings_all()

    def activate_children(self):
        "Activate child trackers and tasks."
        for child in self.children_all():
            child.activate()
        for task in self.tasks.all():
            task.activate()

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
