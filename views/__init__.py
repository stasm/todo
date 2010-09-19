from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required

from todo.forms import AddTaskForm, AddTrackerForm

def new(request):
    return render_to_response('todo/new.html')

@permission_required('todo.create_task')
def new_task(request):
    if request.method == 'POST':
        form = AddTaskForm(request.POST)
        if form.is_valid():
            prototype = form.cleaned_data.pop('prototype')
            fields = form.cleaned_data
            if fields['parent'] is not None:
                # For consistency's sake, if a parent is specified, try to
                # use its values for `project` and `locale` to create the
                # task, ignoring values provided by the user in the form.
                for field in ('project', 'locale'):
                    parent_field_value = getattr(fields['parent'], field)
                    if parent_field_value is not None:
                        fields[field] = parent_field_value
            task = prototype.spawn(**fields)
            task.activate()
            return HttpResponseRedirect(reverse('todo.views.demo.task',
                                                args=[task.pk]))
    else:
        form = AddTaskForm()
    return render_to_response('todo/new_task.html',
                              {'form': form,})

@permission_required('todo.create_tracker')
def new_tracker(request):
    if request.method == 'POST':
        form = AddTrackerForm(request.POST)
        if form.is_valid():
            prototype = form.cleaned_data.pop('prototype')
            tracker = prototype.spawn(**form.cleaned_data)
            redirect_url = reverse('todo.views.demo.tracker',
                                   args=[tracker.pk])
            return HttpResponseRedirect(redirect_url)
    else:
        form = AddTrackerForm()
    return render_to_response('todo/new_tracker.html',
                              {'form': form,})
