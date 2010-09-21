from django.contrib import admin

from todo.models import *
from todo.admin.proto import (ProtoTrackerAdmin, ProtoTaskAdmin,
                              ProtoStepAdmin)

class TaskAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links + ('project', 'locale')
    fieldsets = (
            (None, {'fields': ('summary', 'alias', 'bugid')}),
            ('Status', {'fields': ('status',)}),
            ('Hierarchy', {
                'classes': ('collapse',),
                'fields': ('project', 'locale', 'parent'),
            }),
            ('Under the hood', {
                'classes': ('collapse',),
                'fields': ('prototype', 'snapshot_ts'),
            }),
    )

admin.site.register(Project)
admin.site.register(Actor)
admin.site.register(Tracker)
admin.site.register(Task, TaskAdmin)
admin.site.register(Step)
admin.site.register(ProtoTracker, ProtoTrackerAdmin)
admin.site.register(ProtoTask, ProtoTaskAdmin)
admin.site.register(ProtoStep, ProtoStepAdmin)
