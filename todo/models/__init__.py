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

try:
    from django.dispatch import receiver
except ImportError:
    from todo.signals import receiver

from todo.workflow import RESOLVED
from todo.signals import status_changed, todo_updated

from .action import Action
from .project import Project
from .actor import Actor
from .proto import *
from .tracker import Tracker, TrackerInProject
from .task import Task, TaskInProject
from .step import Step

@receiver(todo_updated)
@receiver(status_changed)
def log_status_change(sender, user, flag, **kwargs):
    """Create a log entry describing the change.

    The logging backend is the default Django's admin one. Log entries are
    available via an `actions` property on todo objects, which returns
    a manager.

    For efficiency reasons, in case of Steps, the resolution time is cached on
    the corresponding Task as well, in `Task.latest_resolution_ts`. It is thus
    readily available for quick queries.

    """
    action = Action.objects.log(user, sender, flag)

    if isinstance(sender, Step) and action.flag >= RESOLVED:
        # a Step has just been resolved, let's store the time of this change on
        # the related Task for faster queries. We don't need to send the signal
        # again for the task as the action has already been recorded for the
        # step.
        sender.task.update(user, {'latest_resolution_ts': action.timestamp},
                           send_signal=False)
