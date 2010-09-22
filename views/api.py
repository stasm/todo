from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from todo.models import Task, Tracker
from todo.forms import UpdateTodoForm

import urllib2
from datetime import datetime
try:
    import json
except ImportError:
    from django.utils import simplejson as json
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder

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
def update_snapshot(request, task_id):
    if not request.user.has_perm('todo.change_task'):
        return _status_response('error', "You don't have permissions to "
                                "update the snapshot timestamp.")
    new_snapshot_ts = datetime.strptime(request.POST.get('snapshot_ts'),
                                        BzAPI.time_format)
    if not new_snapshot_ts:
        return _status_response('error', 'Unknown timestamp (%s)' %
                                request.POST.get('snapshot_ts'))
    task = get_object_or_404(Task, pk=task_id)
    task.update_snapshot(new_snapshot_ts)
    return _status_response('ok', 'Timestamp updated (%s)' %
                            task.snapshot_ts_iso())

@require_POST
def update_bugid(request, task_id):
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
    task.update_bugid(new_bugid)
    return _status_response('ok', 'Bug ID updated (%s)' % task.bugid)

@require_POST
def update(request, obj, obj_id):
    if not request.user.has_perm('todo.change_%s' % obj):
        return _status_response('error', "You don't have permissions to "
                                "update this %s." % obj)
    form = UpdateTodoForm(request.POST)
    if not form.is_valid():
        message = 'There were problems with the following fields:\n'
        for field, errorlist in form.errors.iteritems():
            message += '%s: %s' % (field, errorlist.as_text())
        return _status_response('error', message)
    model = Task if obj == 'task' else Tracker
    todo = get_object_or_404(model, pk=obj_id)
    for prop, new_value in form.cleaned_data.iteritems():
        setattr(todo, prop, new_value)
    todo.save()
    changed_objs = serialize('python', (todo,))
    return _status_response('ok', '%s updated.' % obj, changed_objs)
