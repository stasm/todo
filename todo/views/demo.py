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

from django.shortcuts import get_object_or_404, render_to_response
from django.utils.safestring import mark_safe

from todo.views import snippets

def task(request, task_id):
    from todo.models import Task
    task = get_object_or_404(Task, pk=task_id)
    task_snippet = snippets.task(request, task,
                                 redirect_view='todo.views.demo.task')
    return render_to_response('todo/demo_task.html',
                              {'task_snippet': task_snippet,})

def showcase(request):
    from todo.models import Project
    from life.models import Locale
    if ('project' not in request.GET or
        'locale' not in request.GET):
        raise Exception("No project and/or locale passed as query args.")
    project = get_object_or_404(Project, code=request.GET['project'])
    locale = get_object_or_404(Locale, code=request.GET['locale'])
    open_tasks = snippets.showcase(request, project, locale,
                                   task_view='todo.views.demo.task')
    return render_to_response('todo/demo_showcase.html',
                              {'open_tasks': open_tasks,})

def tracker(request, tracker_id):
    from todo.models import Tracker
    tracker = get_object_or_404(Tracker, pk=tracker_id)
    tree = snippets.tree(request, tracker=tracker,
                         project=None, locale=None,
                         task_view='todo.views.demo.task',
                         tracker_view='todo.views.demo.tracker')
    return render_to_response('todo/demo_tree.html',
                              {'tree': tree,})

def trackers(request):
    from todo.models import Project
    from life.models import Locale
    if ('project' not in request.GET and
        'locale' not in request.GET):
        raise Exception("No project and/or locale passed as query args.")
    project = locale = None
    if 'project' in request.GET:
        project = get_object_or_404(Project, code=request.GET['project'])
    if 'locale' in request.GET:
        locale = get_object_or_404(Locale, code=request.GET['locale'])
    tree = snippets.tree(request, tracker=None,
                         project=project, locale=locale,
                         task_view='todo.views.demo.task',
                         tracker_view='todo.views.demo.tracker')
    return render_to_response('todo/demo_tree.html',
                              {'tree': tree,})
