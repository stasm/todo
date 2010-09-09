from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

from todo.models import Task, Step
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm

@require_POST
@permission_required('todo.change_task')
def resolve_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.resolve()
    return HttpResponseRedirect(reverse('todo.views.task', 
                                        args=(task_id,)))
        
@require_POST
@permission_required('todo.change_step')
def resolve_step(request, step_id):
    step = get_object_or_404(Step, pk=step_id)
    if not step.is_review:
        form = ResolveTodoForm(request.POST)
        if form.is_valid():
            task_id = form.cleaned_data['task_id']
            step.resolve()
            return HttpResponseRedirect(reverse('todo.views.task', 
                                                args=(task_id,)))
    else:
        form = ResolveReviewTodoForm(request.POST)
        if form.is_valid():
            task_id = form.cleaned_data['task_id']
            success = form.cleaned_data['success']
            resolution = 1 if success else 2
            step.resolve(resolution)
            return HttpResponseRedirect(reverse('todo.views.task', 
                                                args=(task_id,)))
