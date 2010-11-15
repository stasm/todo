Installation
============

#. Put the ``todo`` directory in your Python path.

#. Add ``todo`` to your ``INSTALLED_APPS`` setting.

#. Add the following line to your global URL patterns:

    ``(r'^todo/', include('todo.urls')),``

#. Sync the database.

#. Copy ``todo/static`` to wherever you serve your static files from.

#. Include the following code snippet in the ``HEAD`` section of every view
   that will display ``todo``'s snippets::

    <link rel="stylesheet" type="text/css" href="{% url static path='todo/todo.css' %}" />

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


Integration
===========

In order to enable *todo* for your app, follow these steps:

#. Add a one-to-one relation to your app's project model definition pointing to
   ``todo.models.Project``::

    from todo.models import Project as TodoProject

    class YourProject(models.Model):
        ...
        todo = models.OneToOneField(TodoProject, related_name="origin")

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
    from django.utils.safestring import mark_safe

    from todo.views import snippets

    def single_task(request, task_id):
        from todo.models import Task
        task = get_object_or_404(Task, pk=task_id)
        task_div = snippets.task(request, task,
                                 redirect_view='yourapp.views.single_task')
        task_div = mark_safe(task_div)
        return render_to_response('yourapp/single_task.html',
                                  {'task_div': task_div,})

    def single_tracker(request, tracker_id):
        from todo.models import Tracker
        tracker = get_object_or_404(Tracker, pk=tracker_id)
        tree_div = snippets.tree(request, tracker=tracker,
                                 project=None, locale=None,
                                 task_view='yourapp.views.single_task',
                                 tracker_view='yourapp.views.single_tracker')
        tree_div = mark_safe(tree_div)
        return render_to_response('yourapp/single_tracker.html',
                                  {'tree_div': tree_div,})

   See ``todo.views.snippets`` and ``todo.views.demo`` for more documentation.

#. Add the ``todo`` snippets' ``divs`` to your templates. Wrap them in
   a ``div`` with the ``todo`` class. For example:

    ``<div class="todo">{{task_div}}</div>``

   or

    ``<div class="todo">{{tree_div}}</div>``
