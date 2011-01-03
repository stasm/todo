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
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
try:
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
except ImportError:
    LogEntry = None

from todo.workflow import (NEW, ACTIVE, NEXT, ON_HOLD, RESOLVED, COMPLETED,
                           FAILED, INCOMPLETE)

# actions related to status and resolution changes
CREATED = NEW
ACTIVATED = ACTIVE
NEXTED = NEXT
PUT_ON_HOLD = ON_HOLD
RESOLVED = RESOLVED
RESOLVED_COMPLETED = RESOLVED + COMPLETED
RESOLVED_FAILED = RESOLVED + FAILED
RESOLVED_INCOMPLETE = RESOLVED + INCOMPLETE

# other actions
UPDATED = 11
SNAPSHOT_UPDATED = 12
BUGID_UPDATED = 13

actions = {
    CREATED: 'created',
    ACTIVATED: 'activated',
    NEXTED: 'nexted',
    PUT_ON_HOLD: 'put on hold',
    RESOLVED: 'resolved',
    RESOLVED_COMPLETED: 'resolved (completed)',
    RESOLVED_FAILED: 'resolved (failed)',
    RESOLVED_INCOMPLETE: 'resolved (incomplete)',
    UPDATED: 'updated',
    SNAPSHOT_UPDATED: 'snapshot updated',
    BUGID_UPDATED: 'bugid updated',
}

class ActionManager(models.Manager):
    def log(self, user, subject, flag, subject_repr=None, message=None,
            create_logentry=True):
        """Create a log entry about an action that just happened.

        The method creates an Action with `flag` and `message` describing the
        action. If `create_logentry` is True (default) and Django's admin panel
        is installed, it will also create a corresponding LogEntry object which
        is used in admin's history view.

        Arguments:
            user -- The author of the change.
            subject -- The subject that the action is related to. This can be 
                       an instance of any model).
            flag -- A integer representing the type of action. See
                    todo.workflow for values. The value of the flag is a sum
                    of status and resolution flags (i.e. 'resolved failed' is
                    5 + 2 = 7)
            subject_repr -- A string representation of the subject. Optional; 
                           the default is the return value of the __unicode__ 
                           method called on the subject.
            message -- A string with any additional message or comment relevant
                       to the action. Optional.
            create_logentry -- A boolean specifying if a corresponding Django
                               admin panel's LogEntry should be created 
                               alongside the Action. The default is True.

        """
        if message is None:
            message = actions[flag]
        action = self.model(
            timestamp=None,
            user=user,
            subject=subject,
            flag=flag,
            subject_repr=subject_repr or unicode(subject),
            message=message
        )
        action.save()

        # create an entry in the admin panel's log (if admin is enabled)
        if (create_logentry and LogEntry and 
            'django.contrib.admin' in settings.INSTALLED_APPS):
            LogEntry.objects.log_action(
                user_id = action.user.pk,
                content_type_id = action.subject_content_type.pk,
                object_id = action.subject_id,
                object_repr = action.subject_repr,
                action_flag = ADDITION if flag == NEW else CHANGE,
                change_message = action.message
            )

        return action

ACTION_CHOICES = tuple([(i, txt) for i, txt in actions.iteritems()])

class Action(models.Model):
    "A log entry for an action that happened to an object."
    timestamp = models.DateTimeField('timestamp', auto_now=True)
    user = models.ForeignKey(User, related_name='actions')
    subject_content_type = models.ForeignKey(ContentType)
    subject_id = models.PositiveIntegerField()
    subject = generic.GenericForeignKey('subject_content_type', 'subject_id')
    # cache the string representation of the subject
    subject_repr = models.CharField('subject repr', max_length=200, blank=True)
    flag = models.PositiveIntegerField(choices=ACTION_CHOICES)
    message = models.TextField('message', blank=True)

    objects = ActionManager()

    class Meta:
        app_label = 'todo'
        ordering = ('-timestamp',)

    def __unicode__(self):
        return '%s %s' % (self.subject_repr, unicode(self.timestamp))

    def save(self):
        if self.subject_repr is None:
            self.subject_repr = unicode(self.subject)
        self.subject_repr = self.subject_repr[:200]
        super(Action, self).save()

    @models.permalink
    def get_admin_url(self):
        "Return the admin URL to the object related to this action."
        return ('admin:%s_%s_change' % (self.subject_content_type.app_label,
                self.subject_content_type.model), [self.subject_id])
