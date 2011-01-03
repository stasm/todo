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

In order to enable *todo* for your app, follow these steps:

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

   To use the ``createtodoprojects`` command pass the name of your app::

    python manage.py createtodoprojects yourapp

   The command looks by default for a model called *Project* in your app's 
   models. If you named it differently, specify the correct name with the 
   ``--model`` option::

    python manage.py createtodoprojects --model YourProject yourapp

   One todo.Project object will be created for each of your projects.  The 
   default label for todo.Project is whatever ``unicode(yourproject)`` returns.  
   You can override this by passing a Python statement to the ``--label`` 
   option. An exception will be raised if the syntax is not valid.  The 
   statement is evaluated in the current environment of the command, so be 
   careful not to delete your projects accidentally.  Example::

     python manage.py createtodoprojects \
       --model YourProject \
       --label '"%s %s" % (project.line.name, project.version)' \
       yourapp

   The label is always truncated to the first 50 characters.

#. Create or modify views where you want to use the ``todo`` snippets. You must
   have at least two views:
   
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
