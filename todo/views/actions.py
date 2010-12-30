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
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from todo.models import Project, Task, Step
from todo.forms import *

@require_POST
@permission_required('todo.change_task')
def resolve_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    form = ResolveTaskForm(request.POST)
    if form.is_valid():
        redirect_url = form.cleaned_data['redirect_url']
        project_id = form.cleaned_data['project_id']
        project = get_object_or_404(Project, pk=project_id)
        task.resolve(request.user, project)
        return HttpResponseRedirect(redirect_url)
        
@require_POST
@permission_required('todo.change_step')
def resolve_step(request, step_id):
    step = get_object_or_404(Step, pk=step_id)
    if not step.is_review:
        form = ResolveSimpleStepForm(request.POST)
        if form.is_valid():
            redirect_url = form.cleaned_data['redirect_url']
            step.resolve(request.user)
            return HttpResponseRedirect(redirect_url)
    else:
        form = ResolveReviewStepForm(request.POST)
        if form.is_valid():
            redirect_url = form.cleaned_data['redirect_url']
            success = form.cleaned_data['success']
            resolution = 1 if success else 2
            step.resolve(request.user, resolution)
            return HttpResponseRedirect(redirect_url)
