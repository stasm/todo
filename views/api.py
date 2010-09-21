from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from todo.models import Task

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

def _status_response(status, message):
    data = {'status': status,
            'message': message}
    return HttpResponse(json.dumps(data, indent=2),
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
