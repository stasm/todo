# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla todo app.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured

import sys
from optparse import make_option

class Command(BaseCommand):
    args = 'MODEL [MODEL...]'
    option_list = BaseCommand.option_list + (
        make_option(
            '-l',
            '--label',
            action='store',
            type='string',
            dest='label_stmt',
            help="A Python statement that will be evaluated to create labels "
                 "for the todoprojects. It must evaluate to a string. For "
                 "each of your APP's projects, its model's instance is "
                 "available as the `project` variable, which can be used in "
                 "the statement. Example: '\"%s %s\" % "
                 "(project.line, project.version)'. The default is "
                 "'unicode(project)'. The label will be truncated to first 50 "
                 "characters."
        ),
    )

    help = 'Creates todo.Project objects for each instance of MODEL which ' \
           'should be specified in the app_label.model_label syntax.'

    def handle(self, *model_paths, **options):
        from django.db.models import get_model
        from django.contrib.contenttypes.models import ContentType
        from todo.models import Project as TodoProject

        label_stmt = options.get('label_stmt', None)

        if not model_paths:
            raise CommandError('Specify at least one model for which to '
                               'create todoprojects.')

        for model_path in model_paths:
            try:
                app_label, model_label = model_path.split('.')
            except ValueError:
                raise CommandError('Specify the model using the '
                                   'app_label.model_label syntax.')
            model = get_model(app_label, model_label)
            if model is None:
                raise CommandError("Unknown model: %s.%s"
                                   % (app_label, model_label))

            for project in model.objects.all():
                label = eval(label_stmt) if label_stmt else unicode(project)
                if not isinstance(label, basestring):
                    raise CommandError('The label statement must evaluate to '
                                       'a string.')
                label = label[:50]
                print 'Setting up a todoproject for %s' % label
                (todo, created) = TodoProject.objects.get_or_create(
                    label=label,
                    model_ct_id=ContentType.objects.get_for_model(model).pk
                )
                if created:
                    print '  Todoproject with label %s created.' % label
                else:
                    print '  Using an existing todoproject with label %s.' \
                          % label
                print '  Setting up the foreign key...', # no EOL
                project.todo = todo
                project.save()
                print 'done.\n'
