from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect

from life.models import Locale

from todo.models import *
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm
from todo.workflow import statuses
from todo.managers import StatusManager

@require_POST
@permission_required('todo.change_task')
def resolve_task(request, task_id):
    error_message = "Incorrect data"
    try:
        task = Task.objects.get(pk=task_id)
    except KeyError:
        error_message = "Task %s doesn't exist." % task_id
    else:
        task.resolve()
        return HttpResponseRedirect(reverse('todo.views.task', 
                                            args=(task_id,)))
        
    return HttpResponse("%s" % error_message)

@require_POST
@permission_required('todo.change_step')
def resolve_step(request, step_id):
    error_message = "Incorrect data"
    try:
        step = Step.objects.get(pk=step_id)
    except KeyError:
        error_message = "Step %s doesn't exist." % step_id
    else:
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
        
    return HttpResponse("%s" % error_message)

@require_POST
@permission_required('todo.add_todo')
def create(request):
    number_of_bugs = int(request.POST.get('number_of_bugs'))
    form = AddTasksForm(number_of_bugs, request.POST)
    if form.is_valid():
        created_tasks = 0
        prototype = form.cleaned_data.pop('prototype')
        bugs = form.cleaned_data.pop('bugs')
        print bugs
        for bug in bugs:
            for locale in bug['locales']:
                task = Todo.proto.create(prototype, summary=bug['summary'], locale=locale, bug=bug['bugid'], **form.cleaned_data)
                created_tasks += 1
                task.activate()
        if created_tasks == 1:
            redir = reverse('todo.views.task', args=(task.id,))
        else:
            redir = form.cleaned_data['batch'].get_absolute_url()
        return HttpResponseRedirect(redir)
    else:
        error_message = "Incorrect data"
        return render_to_response('todo/new.html', {'form' : form,
                                                    'error_message' : error_message})

@require_POST
def redirect_to_feed(request):
    items = request.POST.get('items')
    if items == 'tasks':
        form = TasksFeedBuilderForm(request.POST)
    else:
        form = NextActionsFeedBuilderForm(request.POST)
    if form.is_valid():
        feed = build_feed(items, form.cleaned_data)
        return HttpResponseRedirect(feed[1])
