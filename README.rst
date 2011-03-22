Installation
============

#. Put the ``todo`` directory in your Python path.

#. Add ``todo`` to your ``INSTALLED_APPS`` setting.

#. Add the following line to your global URL patterns::

    (r'^todo/', include('todo.urls')),

#. Sync the database.

#. Copy ``todo/static`` to wherever you serve your static files from.


Integration
===========

In order to enable *todo* for your app, follow the steps below.


Models
------

#. Add a one-to-one relation to your app's project model definition pointing to
   ``todo.models.Project``::

    from todo.models import Project as TodoProject

    class YourProject(models.Model):
        ...
        todo = models.OneToOneField(TodoProject, related_name="yourapp")

#. Modify the database accordingly. For example::

    ALTER TABLE yourapp_yourproject 
    ADD COLUMN `todo_id` integer NOT NULL UNIQUE;

   You can also run `python manage.py sql yourapp` to see what column definiton 
   Django expects from the addition in the previous step.

#. Optionally, add the new ``todo`` field on your project's model to its admin 
   panel::

    from django.contrib import admin

    from yourapp.models import YourProject

    class YourProjectAdmin(admin.ModelAdmin):
        ...
        fieldsets = (
                ...
                ('Integration', {
                    'classes': ('collapse',),
                    'fields': ('todo',),
                }),
        )

    admin.site.register(YourProject, YourProjectAdmin)

#. Create ``todo.models.Project`` objects corresponding to your app's projects. 
   You'll need to create one object for each project you have.  This can be 
   easily done via your app's admin panel or using the ``createtodoprojects`` 
   management command supplied by ``todo``.

   To use the ``createtodoprojects`` command pass the name of the model from 
   your app that you use to store your projects.  You can specify more than 
   one model.  Use the app_label.model_label syntax::

    python manage.py createtodoprojects yourapp.YourProject

   One todo.Project object will be created for each of your projects.  The 
   default label for todo.Project is whatever ``unicode(yourproject)`` returns.  
   You can override this by passing a Python statement in the ``--label`` 
   option. An exception will be raised if the syntax is not valid or if the 
   statement doesn't evaluate to a string.  The statement is evaluated in the 
   current environment of the command, so be careful not to delete your 
   projects accidentally.  Example::

     python manage.py createtodoprojects \
       --label '"%s %s" % (project.line.name, project.version)' \
       yourapp.YourProject

   The label is always truncated to the first 50 characters.


Tracker and Task Views
----------------------

The views display data about trackers and/or tasks.  ``todo`` provides snippets 
that you can configure in your existing views and include in your templates.

#. Create or modify views in which you want to use the ``todo`` snippets. You 
   must have at least two views:
   
   * a single task view,
   * a single tracker view.

   These two views are *required*. Additionally, you might want to create:

   * a single project view,
   * a single locale view,
   * a combined (project+locale) view.

   You might want to modify your app's URL patterns like so::

    urlpatterns += patterns('yourapp.views',
        (r'^task/(?P<task_id>\d+)$', 'single_task'), 
        (r'^tracker/(?P<tracker_id>\d+)$', 'single_tracker'), 
    )

   (Add more URL patterns if you have more views.)

   Here's an example of how these views can look like::

    from django.shortcuts import get_object_or_404, render_to_response

    from todo.views import snippets

    def single_task(request, task_id):
        from todo.models import Task
        task = get_object_or_404(Task, pk=task_id)
        task_snippet = snippets.task(request, task,
                                     redirect_view='yourapp.views.single_task')
        return render_to_response('yourapp/single_task.html',
                                  {'task_snippet': task_snippet,})

    def single_tracker(request, tracker_id):
        from todo.models import Tracker
        tracker = get_object_or_404(Tracker, pk=tracker_id)
        tree = snippets.tree(request, tracker=tracker,
                             project=None, locale=None,
                             task_view='yourapp.views.single_task',
                             tracker_view='yourapp.views.single_tracker')
        return render_to_response('yourapp/single_tracker.html',
                                  {'tree': tree,})

   See ``todo.views.snippets`` and ``todo.views.demo`` for more documentation.

#. Add the ``todo`` snippets' ``divs`` to your templates. Wrap them in
   a ``div`` with the ``todo`` class. For example::

    <div class="todo">{{task.div}}</div>

   or::

    <div class="todo">{{tree.div}}</div>

   For views showing more than a single task, you can use the ``empty`` element 
   of the dictionary returned by the snippet to show a customized message in 
   case there is nothing to display. For instance::

    {% if not tree.empty %}
      <div class="todo">{{tree.div}}</div>
    {% else %}
      <p>No trackers or tasks to show.</p>
    {% endif %}

#. Include the following code snippet in the ``HEAD`` section of every view
   that will display ``todo``'s snippets::

    <link rel="stylesheet" type="text/css" href="{% url static path='todo/todo.css' %}" />

#. Include the following code snippet in the ``HEAD`` section of every view 
   that will display a single task::

    <style type="text/css">
        .todo #outofdate {
            background-image: url({% url static path="todo/warning.png" %});
        }
        .todo #uptodate {
            background-image: url({% url static path="todo/okay.png" %});
        }
        .todo #checking div {
            background: url({% url static path="loadingAnimation.gif" %}) no-repeat 0 13px;
        }
    </style>


Create-New Interface
--------------------

This is a special view which you can use to configure how new trackers and 
tasks are created.  By default, ``todo`` provides a simple version of this 
interface at ``/todo/new``.  It is very straightforward:  it shows all the 
projects (from all the apps using ``todo``) and doesn't let you redirect to the 
newly created todos after a successul POST request.

It is possible to customize this interface on a per-app basis, thus allowing to 
address the limitations mentioned above.  Follow the steps below to create 
a custom ersion of the create-new interface for you app.

#. Add a create-new view to your urls.py::

    urlpatterns += patterns('yourapp.views',
        (r'^\/new-todo$', 'new_todo'),
    )

#. Create the view specified in urls.py (``yourapp.view.new_todo`` in the 
   example above)::

    from todo.views import new as create_new_wizard

    def new_todo(request):
        def locale_filter(appver):
            """Get a QuerySet of Locales related to the project (appver).

            This function will be run after the user selects a project to 
            create new todos for in the create-new interface.  It allows you to 
            narrow the list of available locales to those that actually make 
            sense for the project chosen by the user.  The returned locales 
            will be displayed in a select box in the form wizard.

            """
            return Locale.objects.filter(appvers=appver)

        appvers = YourProject.objects.filter(is_archived=False)

        config = {
            'projects': appvers,
            'locale_filter': locale_filter,
            'get_template': lambda step: 'yourapp/new_%d.html' % step,
            'task_view': 'yourapp.views.task',
            'tracker_view': 'yourapp.views.tracker',
            'thankyou_view': 'yourapp.views.created',
        }
        return create_new_wizard(request, **config)

   You can control the most important aspects of the wizard's behavior with the 
   ``config`` dict.  It accepts the following keys and values:

   - `projects`: a QuerySet with the project-like objects in your app.  If 
     `None` (or omitted), all `todo.Project` objects will be shown, possibly 
     showing objects from outside of your app as well (if your app is not the 
     only one using ``todo``).

   - `locale_filter`: a function accepting a single argument, `project`, which 
     is an element from the QuerySet passed in `projects` above.  The function 
     should return a QuerySet of `Locales` related to the passed `project`.  If 
     `None` (or omitted), all locale will be displayed regardless of the 
     projects chosen in the first step.

   - `get_template`: a function accepting a single argument, `step`, which is 
     a zero-based integer index of the step of wizard.  It should return 
     a string which is a name of the template to use for the given step.  If 
     `None` (or omitted), the following default will be used::

      'todo/new_%d.html' % step

   - `task_view`: a string name of the view responsible for showing a single 
     task in your application.  It will be used for redirecting the user to the 
     newly created task.  If `None` (or omitted), the generic 'thank you' view 
     will be used, which will not include any link to the newly created task 
     but can be used to inform the user that the request has been processed 
     successfully.  See `thankyou_view` below.

   - `tracker_view`: a string name of the view responsible for showing a single 
     tracker in your application.  It will be used for redirecting the user to 
     the newly created tracker.  If `None` (or omitted), the generic 'thank 
     you' view will be used, which will not include any link to the newly 
     created tracker but can be used to inform the user that the request has 
     been processed successfully.  See `thankyou_view` below.

   - `thankyou_view`: a string name of the generic 'thank you'/'success' view 
     that will be displayed in absence of the `task_view` or `tracker_view`.  
     If `None` (or omitted), the default provided by ``todo`` will be used, 
     i.e. `todo.views.created`.

#. Grant the following permissions to users/groups that should be able to 
   create new trackers and tasks::

    todo.create_tracker
    todo.create_task
