from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required

from todo.models import Tracker
from todo.forms import ChooseParentForm, AddTasksForm, AddTrackersForm
from todo.signals import status_changed

def new(request):
    return render_to_response('todo/new.html')

@permission_required('todo.create_tracker')
@permission_required('todo.create_task')
def create(request, obj):
    if obj == 'tasks':
        form_class = AddTasksForm
    else:
        form_class = AddTrackersForm

    if request.method == 'POST':
        form = form_class(request.POST)
        parent_form = ChooseParentForm(request.POST)
        if form.is_valid() and parent_form.is_valid():
            fields = form.cleaned_data
            parent_clean = parent_form.cleaned_data
            parent = parent_clean['tracker']
            if (parent is None and
                parent_clean['parent_summary']):
                # user wants to create a new tracker which will be the parent
                parent = Tracker(summary=parent_clean['parent_summary'],
                                 locale=parent_clean['parent_locale'],
                                 suffix=parent_clean['parent_suffix'])
                parent.save()
                # send the 'created' signal
                status_changed.send(sender=parent, user=request.user,
                                    action=parent.status)
                parent.activate(request.user)
            if parent is not None:
                try:
                    parent.assign_to_projects(fields['projects'])
                except IntegrityError:
                    # the parent tracker already belongs to these projects
                    pass
                # For consistency's sake, if a parent is specified, try to
                # use its values for `project` and `locale` to create the
                # task, ignoring values provided by the user in the form.
                if parent.locale:
                    fields['locales'] = [parent.locale]
            fields['parent'] = parent
            prototype = form.cleaned_data.pop('prototype')
            if prototype.clone_per_locale is True:
                for todo in prototype.spawn_per_locale(request.user, **fields):
                    todo.activate(request.user)
            else:
                todo = prototype.spawn(request.user, **fields) 
                todo.activate(request.user)
            return HttpResponseRedirect(reverse('todo.views.demo.%s' % obj[:-1],
                                                args=[todo.pk]))
    else:
        form = form_class()
        parent_form = ChooseParentForm()
    return render_to_response('todo/new_%s.html' % obj[:-1],
                              {'form': form,
                               'parent_form': parent_form,})
