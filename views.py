from django.shortcuts import render_to_response, get_object_or_404
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
from todo.forms import ResolveTodoForm, ResolveReviewTodoForm, AddTasksForm, AddTasksManuallyForm, TasksFeedBuilderForm, NextActionsFeedBuilderForm
from todo.workflow import statuses
from todo.managers import StatusManager
from todo.feeds import build_feed

from itertools import groupby


def index(request):
    tasks_orderby_locale = Todo.tasks.active().select_related('locale').order_by('locale__code')
    tasks_by_locale = dict([ (loc, list(tasks)) for loc, tasks in groupby(tasks_orderby_locale, lambda t: t.locale)])
    locales = []
    for locale in Locale.objects.all().order_by('code'):
        try:
            locales.append((locale, tasks_by_locale[locale]))
        except KeyError:
            locales.append((locale, 0))

    active_projects= Project.objects.active().order_by('type')

    ordered_tasks = Todo.tasks.select_related('project').filter(project__in=active_projects).order_by('project')
    tasks_by_project = dict([ (p, list(tasks)) for p, tasks in groupby(ordered_tasks, lambda t: t.project)])
    
    projects_by_type = []
    for t, projects in groupby(active_projects, lambda p: p.type):
        projects_of_type = []
        type = dict(Project._meta.get_field('type').flatchoices)[t]
        for project in projects:
            if tasks_by_project.has_key(project):
                tasks = tasks_by_project[project]
                open_tasks = [task for task in tasks if task.status_is('active')]
                resolved_tasks = [task for task in tasks if task.status_is('resolved')]
                projects_of_type.append({'name': project.name,
                                         'project': project,
                                         'has_tasks': True,
                                         'open': open_tasks,
                                         'resolved': resolved_tasks,
                                         'percent': 100 * len(resolved_tasks) / len(tasks)})
            else:
                projects_of_type.append({'name': project.name,
                                         'project': project,
                                         'has_tasks': False})
        projects_by_type.append((type, projects_of_type))

    return render_to_response('todo/index.html',
                              {'locales' : locales,
                               'projects_by_type' : projects_by_type},
                              context_instance=RequestContext(request))

def project_summary(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    project_tasks = project.tasks.select_related('batch', 'locale').order_by('batch', 'locale')
    
    if not project_tasks:
        return render_to_response('todo/project_summary_empty.html',
                                  {'project' : project})
    
    open_tasks = [task for task in project_tasks if task.status_is('active')]
    resolved_tasks = [task for task in project_tasks if task.status_is('resolved')]
    
    tasks_by_batch = dict([ (b, list(tasks)) for b, tasks in groupby(project_tasks, lambda t: t.batch)])
    batches = []
    for batch in project.batches.all():
        if not tasks_by_batch.has_key(batch):
            batches.append({'name': batch.name,
                            'batch': batch,
                            'has_tasks': False})
            continue
        batch_tasks = tasks_by_batch[batch]
        batch_open_tasks = [task for task in batch_tasks if task.status_is('active')]
        batch_resolved_tasks = [task for task in batch_tasks if task.status_is('resolved')]
        batches.append({'name': batch.name,
                        'batch': batch,
                        'has_tasks': True,
                        'total': batch_tasks,
                        'open': batch_open_tasks,
                        'resolved': batch_resolved_tasks,
                        'open_by_locale' : dict([ (l, list(tasks)) for l, tasks in groupby(batch_open_tasks, lambda t: t.locale)]),
                        'resolved_by_locale' : dict([ (l, list(tasks)) for l, tasks in groupby(batch_resolved_tasks, lambda t: t.locale)]),
                        'percent': 100 * len(batch_resolved_tasks) / len(batch_tasks)})

    if tasks_by_batch.has_key(None):
        other_tasks = tasks_by_batch[None]
        other_open_tasks = [task for task in other_tasks if task.status_is('active')]
        other_resolved_tasks = [task for task in other_tasks if task.status_is('resolved')]
        other = {
            'name': 'Uncategorized tasks',
            'batch': None,
            'has_tasks': True,
            'total': other_tasks,
            'open': other_open_tasks,
            'resolved': other_resolved_tasks,
            'open_by_locale' : dict([ (l, list(tasks)) for l, tasks in groupby(other_open_tasks, lambda t: t.locale)]),
            'resolved_by_locale' : dict([ (l, list(tasks)) for l, tasks in groupby(other_resolved_tasks, lambda t: t.locale)]),
        }
        batches.append(other)

    return render_to_response('todo/project_summary.html',
                              {'project' : project,
                               'batches': batches,
                               'total': project_tasks,
                               'open': open_tasks,
                               'resolved': resolved_tasks,
                               'percent': 100 * len(resolved_tasks) / len(project_tasks)},
                              context_instance=RequestContext(request))

def dashboard(request, locale_code=None, project_slug=None, bug_id=None, status=None):
    
    def _get_feeds(objs, filter_name):
        feeds = []
        for items in ('tasks', 'next'):
            feeds.append(build_feed(items, {filter_name: objs}))
        return feeds

    view = 'everything'
    requested = []
    feeds = []
    order = ['.project', '.batch', '.locale']
    if status in StatusManager.requestable_for_task:
        args = [('status', status)]
    else:
        status = 'open'
        args = []
    if request.GET.has_key('snapshot'):
        args.append(('snapshot', 1))
    if locale_code is not None:
        view = 'locale'
        locales = locale_code.split(',')
        locales = Locale.objects.filter(code__in=locales)
        locale_ids = locales.values_list('code', flat=True)
        if locales:
            requested = locales
            requested_codes = ','.join(locale_ids)
            args += [('locale', loc_id) for loc_id in locale_ids]
            feeds += _get_feeds(locales, 'locale')
            order.remove('.locale')
    elif project_slug is not None:
        view = 'project'
        projects = project_slug.split(',')
        projects = Project.objects.filter(slug__in=projects)
        project_slugs = projects.values_list('slug', flat=True)
        if projects:
            requested = projects
            requested_codes = ','.join(project_slugs)
            args += [('project', project_slug) for project_slug in project_slugs]
            feeds += _get_feeds(projects, 'project')
            order.remove('.project')
    elif bug_id is not None:
        view = 'bug'
        bug_ids = bug_id.split(',')
        bugs = [int(b) for b in bug_ids]
        if bugs:
            requested = bugs
            requested_codes = ','.join(bug_ids)
            args += [('bug', bug) for bug in bugs]
            feeds += _get_feeds(bugs, 'bug')
            order = ['.locale']

    return render_to_response('todo/dashboard.html',
                              {'view' : view,
                               'requested' : requested,
                               'requested_codes' : requested_codes,
                               'status' : status,
                               'feeds' : feeds,
                               'order' : ', '.join(order),
                               'args' : mark_safe(urlencode(args)),
                               'snapshot' : request.GET.has_key('snapshot')},
                              context_instance=RequestContext(request))
    
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
    locales = Locale.objects.all()
    form = AddTasksForm()
    return render_to_response('todo/new.html',
                              {'locales': locales,
                               'form': form},
                              context_instance=RequestContext(request))

@login_required
def new_manually(request):
    error_message = None
    form = AddTasksManuallyForm()
    return render_to_response('todo/new_manually.html', 
                              {'form' : form,
                               'error_message' : error_message},
                              context_instance=RequestContext(request))

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

def feed_builder(request):
    task_form = TasksFeedBuilderForm()
    next_form = NextActionsFeedBuilderForm()
    return render_to_response('todo/feed_builder.html',
                              {'task_form': task_form,
                               'next_form': next_form},
                              context_instance=RequestContext(request))

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
