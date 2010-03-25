from django.shortcuts import render_to_response
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.template import Context, loader
from django.http import HttpResponse, HttpResponseNotFound,\
    HttpResponseNotModified, HttpResponseRedirect
from django.utils import simplejson

from todo.models import Todo
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm, AddTodoFromProtoForm

from todo.workflow import statuses


def index(request):
    tasks = Todo.tasks.active()
    return render_to_response('todo/index.html',
                       {'tasks' : tasks,
                        'statuses' : statuses})
    
def task(request, task_id):
    task = Todo.objects.get(pk=task_id)
    return render_to_response('todo/details.html',
                              {'task' : task,
                               'statuses' : statuses})
                        
@require_POST
def resolve(request, todo_id):
    error_message = "Incorrect data"
    try:
        todo = Todo.objects.get(pk=todo_id)
    except KeyError:
        error_message = "Todo %s doesn't exist." % todo_id
    else:
        if not todo.is_review:
            form = ResolveTodoForm(request.POST)
            if form.is_valid():
                task_id = form.cleaned_data['task_id']
                todo.resolve()
                return HttpResponseRedirect(reverse('todo.views.task', 
                                                    args=(task_id,)))
        else:
            form = ResolveReviewTodoForm(request.POST)
            if form.is_valid():
                task_id = form.cleaned_data['task_id']
                success = form.cleaned_data['success']
                resolution = 1 if success else 2
                todo.resolve(resolution)
                return HttpResponseRedirect(reverse('todo.views.task', 
                                                    args=(task_id,)))
        
    return HttpResponse("%s" % error_message)

def new(request):
    error_message = None
    form = AddTodoFromProtoForm()
    return render_to_response('todo/new.html', {'form' : form,
                                                'error_message' : error_message})

@require_POST
def create(request):
    form = AddTodoFromProtoForm(request.POST)
    if form.is_valid():
        prototype = form.cleaned_data.pop('prototype')
        custom_fields = form.cleaned_data
        task = Todo.proto.create(prototype, **custom_fields)
        task.activate()
        return HttpResponseRedirect(reverse('todo.views.task', 
                                            args=(task.id,)))
    else:
        error_message = "Incorrect data"
        return render_to_response('todo/new.html', {'form' : form,
                                                    'error_message' : error_message})

