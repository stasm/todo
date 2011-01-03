from django.core.management.base import AppCommand, CommandError

import sys
from optparse import make_option

from todo.models import Project as TodoProject

class Command(AppCommand):
    args = 'APP'
    option_list = AppCommand.option_list + (
        make_option(
            '-m',
            '--model',
            action='store',
            type='string',
            dest='model',
            help="A model in APP for which todoprojects will be created. The "
                 "default is 'Project'."
        ),
        make_option(
            '-l',
            '--label',
            action='store',
            type='string',
            dest='label',
            help="A Python statement that will be evaluated to create labels "
                 "for the todoprojects. For each of your APP's projects, its "
                 "model's instance is available as the `project` variable, "
                 "which can be used in the statement. Example: '\"%s %s\" % "
                 "(project.line, project.version)'. The default is "
                 "'unicode(project)'. The label will be truncated to first 50 "
                 "characters."
        ),
    )

    help = 'Creates todo.Project objects for each instance of project model ' \
           'in the APP. Specify the project model name with --model.'

    def handle_app(self, app, **options):
        model_name = options['model'] or 'Project'
        try:
            model = getattr(app, model_name)
        except AttributeError:
            raise CommandError('Could not find model "%s" in app "%s". '
                               'Make sure the --model option is correct.'
                               % (model_name, app))
        for project in model.objects.all():
            if options['label']:
                label = eval(options['label'])
            else:
                label = unicode(project)
            label = label[:50]
            sys.stdout.write('Creating a todoproject for %s with label %s...'
                              % (project, label))
            (todo, created) = TodoProject.objects.get_or_create(label=label)
            project.todo = todo
            project.save()
            sys.stdout.write(' done.\n')
