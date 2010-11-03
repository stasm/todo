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
        action = self.model(timestamp=None, user=user, subject=subject,
                            flag=flag, subject_repr=subject_repr,
                            message=message)
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
