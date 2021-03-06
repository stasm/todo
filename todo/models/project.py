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

from django.db import models

from todo.workflow import NEW, ACTIVE, NEXT, ON_HOLD

class Project(models.Model):
    label = models.CharField(max_length=50)
    # ID of the ContentType object representing the project-equivalent model 
    # in an app using todo
    model_ct_id = models.PositiveIntegerField("Id of the related model's "
                                              "content type")

    class Meta:
        app_label = 'todo'
        unique_together = ('label', 'model_ct_id')

    def __unicode__(self):
        return '%s' % self.label

    def task_count(self, locale=None):
        if locale is not None:
            tasks = self.tasks.filter(locale=locale)
        else:
            tasks = self.tasks
        all = tasks.count()
        # status and resolution are kept on the intermediary `TaskInProject`
        # model
        open = tasks.filter(statuses__status__lt=ON_HOLD).distinct().count()
        return {'all': all,
                'open': open,
                'completion': 100 * (all - open) / all if all != 0 else 0,
               }

    def open_tasks(self, locale):
        return self.tasks.filter(locale=locale,
                                 statuses__status__in=(NEW, ACTIVE, NEXT))
