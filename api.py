from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from life.models import Locale
from todo.models import Project, Batch, Todo

import urllib2
import json
from datetime import datetime

class BzAPI(object):
    _baseurl = "https://api-dev.bugzilla.mozilla.org/stage/latest/"
    time_format = r'%Y-%m-%dT%H:%M:%SZ'
    
    def __init__(self):
        self._bugs = {}
    
    def last_modified(self, bugid):
        if self._bugs.has_key(bugid):
            return self._bugs[bugid]
        req = urllib2.Request("%s/bug/%s" % (self._baseurl, bugid))
        bugdata = json.load(urllib2.urlopen(req))
        last_modified_time = datetime.strptime(bugdata['last_change_time'], self.time_format)
        self._bugs.update({bugid: last_modified_time})
        return last_modified_time

schema = {
    "types": {
        "Task": {
            "pluralLabel": "Tasks"
            },
        "Next Action": {
            "pluralLabel": "Next actions"
            }
        },
    "properties": {
        "changed": {
            "valueType": "number"
            }
        }
    }

def tasks(request):
    bzapi = BzAPI()
    items = []
    show_resolved = request.GET.get('show_resolved', 0)
    if int(show_resolved) == 1:
        tasks = Todo.tasks.all()
    else:
        tasks = Todo.tasks.active()
    tasks = tasks.select_related('locale', 'project', 'batch', 'prototype')
    
    if request.GET.has_key('bug'):
        bugs = request.GET.getlist('bug')
        bugs = [int(bug) for bug in bugs]
        tasks = tasks.filter(bug__in=bugs)
    if request.GET.has_key('locale'):
        locales = request.GET.getlist('locale')
        locales = Locale.objects.filter(code__in=locales)
        tasks = tasks.filter(locale__in=locales)
    if request.GET.has_key('project'):
        projects = request.GET.getlist('project')
        projects = Project.objects.filter(slug__in=projects)
        tasks = tasks.filter(project__in=projects)
        if request.GET.has_key('batch'):
            batches = request.GET.getlist('batch')
            batches = Batch.objects.filter(slug__in=batches)
            tasks = tasks.filter(batch__in=batches)
    
    task_items = []
    for task in tasks:
        task_data = {'type': 'Task',
                     'id': task.pk,
                     'pk': task.pk,
                     'uri': 'http://%s%s' % (request.get_host(), task.get_absolute_url()),
                     'label': unicode(task),
                     'status': task.get_status_display(),
                     'snapshot_ts': task.snapshot_ts_iso(),
                     'locale': unicode(task.locale),
                     'locale_code': task.locale.code,
                     'project': unicode(task.project),
                     'project_slug': task.project.slug,
                     'batch': unicode(task.batch) if task.batch is not None else 'Other',
                     'prototype': unicode(task.prototype)}
        if task.bug is not None:
            task_data.update({'bug': task.bug})
            if request.GET.has_key('snapshot'):
                bug_ts = bzapi.last_modified(task.bug)
                task_data.update({'snapshot': 'uptodate' if task.is_uptodate(bug_ts) else 'outofdate'})
        task_items.append(task_data)
    items += task_items
    
    next_actions = Todo.objects.next().filter(task__in=tasks).select_related('task', 'owner')
    next_actions_items = []
    for action in next_actions:
        next_actions_items.append({'type': 'Next Action',
                                   'id': action.pk,
                                   'label': unicode(action),
                                   'task': action.task.id,
                                   'owner': unicode(action.owner)})

    items += next_actions_items
    data = {'items': items}
    data.update(schema)
    return HttpResponse(simplejson.dumps(data, indent=2), mimetype='application/javascript')

def _status_response(status, message):
    data = {'status': status,
            'message': message}
    return HttpResponse(simplejson.dumps(data, indent=2), mimetype='application/javascript')

@require_POST
def update_snapshot(request, task_id):
    if not request.user.has_perm('todo.change_todo'):
        return _status_response('error', "You don't have permissions to update the snapshot timestamp.")
    new_snapshot_ts = datetime.strptime(request.POST.get('snapshot_ts'), BzAPI.time_format)
    if not new_snapshot_ts:
        return _status_response('error', 'Unknown timestamp (%s)' % request.POST.get('snapshot_ts'))
    task = Todo.objects.get(pk=task_id)
    task.update_snapshot(new_snapshot_ts)
    return _status_response('ok', 'Timestamp updated (%s)' % task.snapshot_ts_iso())
