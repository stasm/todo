# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla todo app.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from django.db import models

from life.models import Locale

from .action import ACTIVATED
from .base import Todo
from .project import Project
from .proto import ProtoTracker
from todo.managers import StatusManager
from todo.workflow import (NEW, ACTIVE, NEXT, ON_HOLD, RESOLVED, COMPLETED,
                           FAILED, INCOMPLETE, STATUS_CHOICES,
                           RESOLUTION_CHOICES)
from todo.signals import status_changed

class TrackerInProject(models.Model):
    tracker = models.ForeignKey('Tracker', related_name="statuses")
    project = models.ForeignKey(Project, related_name="tracker_statuses")
    status = models.PositiveIntegerField(choices=STATUS_CHOICES, default=NEW)
    resolution = models.PositiveIntegerField(choices=RESOLUTION_CHOICES,
                                             null=True, blank=True)

    class Meta:
        app_label = 'todo'
        unique_together = ('tracker', 'project')

    def __unicode__(self):
        return '%s for %s' % (self.tracker, self.project)

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
    bugid = models.PositiveIntegerField(null=True, blank=True)
    alias = models.SlugField(max_length=200, null=True, blank=True)
    # a cached string representation of the tracker
    _repr = models.CharField(max_length=250, blank=True)

    objects = StatusManager()

    class Meta:
        app_label = 'todo'

    # a list of additional argument names that can be passed to __init__
    extra_fields = ['suffix']

    def __init__(self, *args, **kwargs):
        """Initialize a Tracker object.

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

    def format_repr(self, **kwargs):
        """Get a formatted string representation of the todo object."""

        _repr = self.summary
        # if kwargs are given, mask self.locale using the locale in kwargs
        locale = kwargs.get('locale', None) if kwargs else self.locale
        if locale:
            _repr = '[%s] %s' % (locale.code, _repr)
        return _repr

    def save(self, force=False, *args, **kwargs):
        if (not self.id and not self._repr) or force:
            # the tracker doesn't exist in the DB yet
            self.repr = self.format_repr()
        super(Tracker, self).save(*args, **kwargs)

    def assign_to_projects(self, projects, status=NEW):
        for project in projects:
            TrackerInProject.objects.create(tracker=self, project=project,
                                            status=status)
    
    @property
    def code(self):
        return str(self.id)
    
    @models.permalink
    def get_admin_url(self):
        return ('admin:todo_tracker_change', [self.id])

    def is_generic(self):
        # just check the ID, no need to retrieve the prototype if it exists
        return self.prototype_id is None

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
            return self.parent.children_all()

    def activate(self, user):
        "Activate the tracker across all related projects."

        self.activate_children(user)
        for status in self.statuses.all():
            status.status = ACTIVE
            status.save()
            status_changed.send(sender=status, user=user, flag=ACTIVATED)

    def activate_children(self, user):
        "Activate child trackers and tasks."
        for child in self.children_all():
            child.activate(user)
        for task in self.tasks.all():
            task.activate(user)

    def resolve(self, user, project, resolution=COMPLETED):
        "Resolve the tracker."
        status = self.statuses.get(project=project)
        status.status = RESOLVED
        status.resolution = resolution
        status.save()
        flag = RESOLVED + resolution
        status_changed.send(sender=status, user=user, flag=flag)

    def get_bug(self):
        return self.bugid or self.alias

    def set_bug(self, val):
        if isinstance(val, int):
            self.bugid = val
        else:
            self.bugid = None
            self.alias = val
    
    bug = property(get_bug, set_bug)
