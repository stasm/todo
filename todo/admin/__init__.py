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
