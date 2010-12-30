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

from django.contrib import admin

from todo.models import *
from todo.admin.proto import (ProtoTrackerAdmin, ProtoTaskAdmin,
                              ProtoStepAdmin)

class ActionAdmin(admin.ModelAdmin):
    list_display_links = ('timestamp',)
    list_display = ('id', 'timestamp', 'user', 'subject_repr', 'flag')

class TaskInProjectInline(admin.TabularInline):
    model = TaskInProject
    verbose_name_plural = 'Projects'
    extra = 1

class TaskAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id', 'summary', 'locale',)
    inlines = [TaskInProjectInline]
    fieldsets = (
            (None, {'fields': ('summary', 'alias', 'bugid')}),
            ('Hierarchy', {
                'classes': ('collapse',),
                'fields': ('locale', 'parent'),
            }),
            ('Under the hood', {
                'classes': ('collapse',),
                'fields': ('prototype', 'snapshot_ts', 'latest_resolution_ts',
                           '_repr'),
            }),
    )

admin.site.register(Action, ActionAdmin)
admin.site.register(Project)
admin.site.register(Actor)
admin.site.register(Tracker)
admin.site.register(Task, TaskAdmin)
admin.site.register(Step)
admin.site.register(TaskInProject)
admin.site.register(TrackerInProject)
admin.site.register(ProtoTracker, ProtoTrackerAdmin)
admin.site.register(ProtoTask, ProtoTaskAdmin)
admin.site.register(ProtoStep, ProtoStepAdmin)
