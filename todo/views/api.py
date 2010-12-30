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

from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder

from todo.models import Step, Task, Tracker
from todo.models.action import SNAPSHOT_UPDATED, BUGID_UPDATED
from todo.forms import UpdateTodoForm

import urllib2
from datetime import datetime
try:
    import json
except ImportError:
    from django.utils import simplejson as json

class BzAPI(object):
    _baseurl = "https://api-dev.bugzilla.mozilla.org/latest/"
    time_format = r'%Y-%m-%dT%H:%M:%SZ'
    
    def __init__(self):
        self._bugs = {}
    
    def last_modified(self, bugid):
        if self._bugs.has_key(bugid):
            return self._bugs[bugid]
        req = urllib2.Request("%s/bug/%s" % (self._baseurl, bugid))
        bugdata = json.load(urllib2.urlopen(req))
        last_modified_time = datetime.strptime(bugdata['last_change_time'],
                                               self.time_format)
        self._bugs.update({bugid: last_modified_time})
        return last_modified_time

def _status_response(status, message, data=None):
    response = {'status': status,
                'message': message,
                'data': data}
    return HttpResponse(json.dumps(response, indent=2, cls=DjangoJSONEncoder),
                        mimetype='application/javascript')

@require_POST
def reset_time(request, step_id):
    "Reset the last activity timestamp for a Step to now."

    if not request.user.has_perm('todo.change_step'):
        # this permission is apparently enough, no need to requied
        # `admin.add_logentry` on top of that.  Note that this view doesn't
        # really change the step; it creates a LogEntry instead.  It makes more
        # sense to check for right to change steps, however.
        return _status_response('error', "You don't have permissions to "
                                "change this step.")
    step = get_object_or_404(Step, pk=step_id)
    # `reset_time` will send the correct signal (in fact, it does just that),
    # so there's no need to send it explicitly here.
    step.reset_time(request.user)
    return _status_response('ok', "Step's timer reset. You have %d days, "
                            "again." % step.allowed_time)

@require_POST
def update(request, obj, obj_id):
    """Update various properties of a todo object.

    This method expects all the values to be in the `request.POST`. More 
    specifically, `todo.forms.UpdateTodoForm` defines which properties
    are accepted and which are required.

    Arguments:
    obj -- the model of the todo object to be changed
    obj_id -- the ID of the todo object to be changed

    """
    if not request.user.has_perm('todo.change_%s' % obj):
        return _status_response('error', "You don't have permissions to "
                                "update this %s." % obj)
    model = Task if obj == 'task' else Tracker
    form = UpdateTodoForm(request.POST)
    if not form.is_valid():
        message = 'There were problems with the following fields:\n'
        for field, errorlist in form.errors.iteritems():
            message += '%s: %s' % (field, errorlist.as_text())
        return _status_response('error', message)
    todo = get_object_or_404(model, pk=obj_id)
    todo.update(request.user, form.cleaned_data)
    changed_objs = serialize('python', (todo,))
    return _status_response('ok', '%s updated.' % obj, changed_objs)

@require_POST
def update_snapshot(request, task_id):
    "Specifically update the snapshot timestamp."

    if not request.user.has_perm('todo.change_task'):
        return _status_response('error', "You don't have permissions to "
                                "update the snapshot timestamp.")
    new_snapshot_ts = datetime.strptime(request.POST.get('snapshot_ts'),
                                        BzAPI.time_format)
    if not new_snapshot_ts:
        return _status_response('error', 'Unknown timestamp (%s)' %
                                request.POST.get('snapshot_ts'))
    task = get_object_or_404(Task, pk=task_id)
    task.update(request.user, {'snapshot_ts': new_snapshot_ts},
                flag=SNAPSHOT_UPDATED)
    return _status_response('ok', 'Timestamp updated (%s)' %
                            task.snapshot_ts_iso())

@require_POST
def update_bugid(request, task_id):
    "Specifically update the bug ID."

    if not request.user.has_perm('todo.change_task'):
        return _status_response('error', "You don't have permissions to "
                                "update the bug ID of this task.")
    new_bugid = request.POST.get('bugid', None)
    try:
        new_bugid = int(new_bugid)
    except ValueError, TypeError:
        return _status_response('error', 'Incorrect value of the bug ID (%s)' %
                                request.POST.get('bugid'))
    task = get_object_or_404(Task, pk=task_id)
    task.update(request.user, {'bug': new_bugid}, flag=BUGID_UPDATED)
    return _status_response('ok', 'Bug ID updated (%s)' % task.bugid)
