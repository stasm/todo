from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from todo.models import Task

def task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    return render_to_response('todo/details.html',
                              {'task': task},
                              context_instance=RequestContext(request))
