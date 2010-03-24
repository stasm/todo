from django.shortcuts import render_to_response
from django.views.decorators.http import require_http_methods
from django.core.urlresolvers import reverse
from django.template import Context, loader
from django.http import HttpResponse, HttpResponseNotFound,\
    HttpResponseNotModified, HttpResponseRedirect
from django.utils import simplejson

from todo.models import Todo
from todo.forms import ChangeTodoForm, AddTodoFromProtoForm

from todo.workflow import statuses


def index(request):
    tasks = Todo.objects.get_open_tasks()
    return render_to_response('todo/index.html',
                       {'tasks' : tasks,
                        'statuses' : statuses})
    
def details(request, todo_id):
    todo = Todo.objects.get(pk=todo_id)
    return render_to_response('todo/details.html',
                       {'todo' : todo,
                        'statuses' : statuses})
                        
@require_http_methods(["POST"])
def change(request, todo_id):
    form = ChangeTodoForm(request.POST)
    error_message = "Incorrect data"
    if form.is_valid():
        try:
            todo = Todo.objects.get(pk=todo_id)
        except KeyError:
            error_message = "Todo %s doesn't exist." % todo_id
        else:
             new_status = form.cleaned_data['status']
             todo.status = new_status
             todo.save()
             return HttpResponseRedirect(reverse('todo.views.changed', 
                                                 args=(todo_id,)))
    return HttpResponse("%s" % error_message)

def changed(request, todo_id):
    todo = Todo.objects.get(pk=todo_id)
    return HttpResponse("Todo %s has been changed. The new status is %s" % (todo_id, todo.get_status_display()))

def new(request):
    error_message = None
    form = AddTodoFromProtoForm()
    return render_to_response('todo/new.html', {'form' : form,
                                                'error_message' : error_message})

@require_http_methods(["POST"])
def create(request):
    form = AddTodoFromProtoForm(request.POST)
    if form.is_valid():
        prototype = form.cleaned_data.pop('prototype')
        custom_fields = form.cleaned_data
        task = Todo.proto.create(prototype, **custom_fields)
        task.activate()
        return HttpResponseRedirect(reverse('todo.views.created', 
                                             args=(task.id,)))
    else:
        error_message = "Incorrect data"
        return render_to_response('todo/new.html', {'form' : form,
                                                    'error_message' : error_message})
                                                
def created(request, todo_id):
    todo = Todo.objects.get(pk=todo_id)
    return HttpResponse("Todo %s has been created." % (todo_id,))
    
    