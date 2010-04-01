from django.shortcuts import render_to_response
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.core.urlresolvers import reverse
from django.template import Context, RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from life.models import Locale

from todo.models import Project, Batch, Todo
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm, AddTodoFromProtoForm
from todo.workflow import statuses

from itertools import groupby


def index(request):
    tasks_orderby_locale = Todo.tasks.active().select_related('locale').order_by('locale__code')
    tasks_by_locale = dict([ (loc, len(list(tasks))) for loc, tasks in groupby(tasks_orderby_locale, lambda t: t.locale)])
    locales = []
    for locale in Locale.objects.all().order_by('code'):
        try:
            locales.append((locale, tasks_by_locale[locale]))
        except KeyError:
            locales.append((locale, 0))

    active_projects= Project.objects.active().order_by('type')
    active_batches= Batch.objects.active().select_related('project').order_by('project')
    batches_by_project = dict([ (project, list(batches)) for project, batches in groupby(active_batches, lambda t: t.project)])

    ordered_tasks = Todo.tasks.select_related('project', 'batch').filter(project__in=active_projects).order_by('project', 'batch')
    tasks_by_project = dict([ (p, list(tasks)) for p, tasks in groupby(ordered_tasks, lambda t: t.project)])
    tasks_by_batch = dict([ (p, list(tasks)) for p, tasks in groupby(ordered_tasks, lambda t: t.batch)])
    
    projects_by_type = []
    for t, projects in groupby(active_projects, lambda p: p.type):
        projects_of_type = []
        type = dict(Project._meta.get_field('type').flatchoices)[t]
        for project in projects:
            batches = []
            if batches_by_project.has_key(project):
                for batch in batches_by_project[project]:
                    if tasks_by_batch.has_key(batch):
                        tasks = tasks_by_batch[batch]
                        all_tasks = len(tasks)
                        open_tasks = len([task for task in tasks if task.status == 2])
                        batches.append((batch, {'has_tasks': True,
                                                'open': open_tasks,
                                                'all': all_tasks,
                                                'percent': 100 * (all_tasks - open_tasks) / all_tasks}))
                    else:
                        batches.append((batch, {'has_tasks': False}))
            if tasks_by_project.has_key(project):
                tasks = tasks_by_project[project]
                all_tasks = len(tasks)
                open_tasks = len([task for task in tasks if task.status == 2])
                projects_of_type.append((project, {'batches': batches,
                                                   'has_tasks': True,
                                                   'open': open_tasks,
                                                   'all': all_tasks,
                                                   'percent': 100 * (all_tasks - open_tasks) / all_tasks}))
            else:
                projects_of_type.append((project, {'batches': batches, 
                                                   'has_tasks': False}))
        projects_by_type.append((type, projects_of_type))

    return render_to_response('todo/index.html',
                              {'locales' : locales,
                               'projects_by_type' : projects_by_type},
                              context_instance=RequestContext(request))
    
def dashboard(request):
    title = 'Tasks'
    subtitle = None
    order = ['.project', '.batch', '.label']
    show_resolved = request.GET.get('show_resolved', 0)
    args = [('show_resolved', show_resolved)]
    if request.GET.has_key('locale'):
        locales = request.GET.getlist('locale')
        locales = Locale.objects.filter(code__in=locales)
        locale_names = [unicode(locale) for locale in locales]
        locales = locales.values_list('code', flat=True)
        if locales:
            args += [('locale', loc) for loc in locales]
            title += ' for %s' % ', '.join(locale_names)
    if request.GET.has_key('project'):
        projects = request.GET.getlist('project')
        projects = Project.objects.filter(slug__in=projects)
        projects_names = [unicode(project) for project in projects]
        projects = projects.values_list('slug', flat=True)
        if projects:
            args += [('project', project) for project in projects]
            title += ' for %s' % ', '.join(projects_names)
            order.remove('.project')
            if request.GET.has_key('batch'):
                batches = request.GET.getlist('batch')
                batches = Batch.objects.filter(slug__in=batches, project__slug__in=projects)
                batch_names = [unicode(batch) for batch in batches]
                batches = batches.values_list('slug', flat=True)
                if batches:
                    args += [('batch', batch) for batch in batches]
                    subtitle = 'Batch: %s' % ', '.join(batch_names)
                    order.remove('.batch')

    query = request.GET.copy()
    query['show_resolved'] = 1       
    return render_to_response('todo/dashboard.html',
                              {'title' : title,
                               'subtitle' : subtitle,
                               'order' : ', '.join(order),
                               'args' : mark_safe(urlencode(args)),
                               'show_resolved_path' : request.path + '?' + query.urlencode()},
                              context_instance=RequestContext(request))

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

def tasks_json(request):
    items = []
    show_resolved = request.GET.get('show_resolved', 0)
    if int(show_resolved) == 1:
        tasks = Todo.tasks.all()
    else:
        tasks = Todo.tasks.active()
    tasks = tasks.select_related('locale', 'project', 'batch', 'prototype')
    
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
                     'pk': task.pk,
                     'label': unicode(task),
                     'status': task.get_status_display(),
                     'locale': unicode(task.locale),
                     'locale_code': task.locale.code,
                     'project': unicode(task.project),
                     'project_slug': task.project.slug,
                     'prototype': unicode(task.prototype)}
        if task.batch is not None:
            task_data.update({'batch': unicode(task.batch),
                              'batch_slug': task.batch.slug,})
        task_items.append(task_data)
    items += task_items
    
    next_actions = Todo.objects.next().filter(task__in=tasks).select_related('task', 'owner')
    next_actions_items = []
    for action in next_actions:
        next_actions_items.append({'type': 'Next Action',
                                   'label': unicode(action),
                                   'task': unicode(action.task),
                                   'owner': unicode(action.owner)})

    items += next_actions_items
    data = {'items': items}
    data.update(schema)
    return HttpResponse(simplejson.dumps(data, indent=2))
    
def task(request, task_id):
    task = Todo.objects.get(pk=task_id)
    return render_to_response('todo/details.html',
                              {'task' : task},
                              context_instance=RequestContext(request))
                        
@require_POST
@permission_required('todo.change_todo')
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

@login_required
def new(request):
    error_message = None
    form = AddTodoFromProtoForm()
    return render_to_response('todo/new.html', 
                              {'form' : form,
                               'error_message' : error_message},
                              context_instance=RequestContext(request))

@require_POST
@login_required
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
