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
from django.db.models import Q
from django.contrib.contenttypes import generic

from .action import Action, UPDATED
from todo.workflow import NEW, ACTIVE, NEXT
from todo.signals import todo_updated

class TodoInterface(object):
    """An interface class for all todo objects."""

    def __unicode__(self):
        raise NotImplementedError()

    def format_repr(self, **kwargs):
        """Get a formatted string representation of the todo object.

        Kwargs can be used to pass additional information needed to create the 
        value of the representation.

        """
        raise NotImplementedError()

    @property
    def code(self):
        raise NotImplementedError()

    def get_admin_url(self):
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=600544
        raise NotImplementedError()

    def children_all(self):
        """Get the immediate children of the todo object.

        In its simplest form, this method just calls `all` on the todo object's
        `children` manager.  It does more if called on a Task.  By calling
        `children_all` you make sure that the returned value is a QuerySet, no
        matter which model's instance you called it on.

        See todo.models.Task.children_all for more docs.
        
        """
        raise NotImplementedError()

    def siblings_all(self):
        """Get a QuerySet with the siblings of the current todo object.
        
        Since it returns a QuerySet, the name is `siblings_all` rather than
        `siblings`, in order to help avoid confusion (similar to `children_all`
        above).
 
        """
        raise NotImplementedError()

    def clone(self):
        raise NotImplementedError()

    def resolve(self):
        raise NotImplementedError()

    def activate(self):
        raise NotImplementedError()

    def activate_children(self):
        raise NotImplementedError()

class Todo(TodoInterface, models.Model):
    """Common methods for all todo objects (trackers, tasks, steps)"""

    def __unicode__(self):
        """Return the cached representation of the object."""
        return self.repr

    def get_repr(self):
        if not self._repr:
            self._repr = self.format_repr()
            self.save()
        return self._repr

    def set_repr(self, value):
        self._repr = value

    repr = property(get_repr, set_repr)

    # signals log actions using LogEntry
    actions = generic.GenericRelation(Action, object_id_field="subject_id",
                                    content_type_field="subject_content_type")

    class Meta:
        app_label ='todo'
        abstract = True

    def status_is(self, status_adj):
        return self.get_status_display() == status_adj

    def is_open(self):
        return self.status in (NEW, ACTIVE, NEXT)

    def is_next(self):
        return self.status == NEXT

    def get_actions(self, flag=None):
        if flag is None:
            return self.actions.all()
        return self.actions.filter(flag=flag)

    def get_latest_action(self, flag=None):
        return self.get_actions(flag).latest('timestamp')

    def activate_children(self, user):
        to_activate = self.children_all().filter(Q(is_auto_activated=True) |
                                                 Q(order=1))
        if len(to_activate) == 0:
            to_activate = self.children_all()
        for child in to_activate:
            child.activate(user)

    def update(self, user, properties, send_signal=True, flag=UPDATED):
        """Update properties of the todo object.

        Arguments:
            user -- the author of the change
            properties -- a dict with new values for the properties
            send_signal -- a boolean defining whether to send a `todo_updated`
                           signal or not (default is True)
            flag -- a flag to be sent in the signal (default is UPDATED)

        """
        for prop, new_value in properties.iteritems():
            setattr(self, prop, new_value)
        # if any of these properties change, we need to force the update of all 
        # cached representation strings stored on the todo object
        force_needed = ('summary', 'locale', 'prototype')
        if any(prop in force_needed for prop in properties.keys()):
            self.save(force=True)
        else:
            self.save()
        if send_signal:
            todo_updated.send(sender=self, user=user, flag=flag)
