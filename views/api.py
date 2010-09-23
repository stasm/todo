from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder

from todo.models import Step, Task, Tracker
from todo.forms import UpdateTodoForm
from todo.signals import (status_changed, todo_updated, UPDATED,
                          SNAPSHOT_UPDATED, BUGID_UPDATED)

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
    for prop, new_value in form.cleaned_data.iteritems():
        setattr(todo, prop, new_value)
    todo.save()
    todo_updated.send(sender=todo, user=request.user, action=UPDATED)
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
    task.snapshot_ts = new_snapshot_ts
    task.save()
    todo_updated.send(sender=task, user=request.user, action=SNAPSHOT_UPDATED)
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
    task.bug = new_bugid
    task.save()
    todo_updated.send(sender=task, user=request.user, action=BUGID_UPDATED)
    return _status_response('ok', 'Bug ID updated (%s)' % task.bugid)
