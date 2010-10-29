from django.contrib import admin

from todo.models import *
from todo.admin.forms import (ProtoTrackerSet, ProtoTrackerForm,
                              ProtoTaskSet, ProtoTaskForm,
                              ProtoStepSet, ProtoStepForm)

class TrackerNestingInline(admin.TabularInline):
    model = Nesting
    fk_name = 'child'
    formset = ProtoTrackerSet
    form = ProtoTrackerForm
    verbose_name_plural = 'Parent Proto Trackers'
    extra = 3

class TaskNestingInline(admin.TabularInline):
    model = Nesting
    fk_name = 'child'
    formset = ProtoTaskSet
    form = ProtoTaskForm
    verbose_name_plural = 'Parent Proto Tasks'
    extra = 3

class StepNestingInline(admin.TabularInline):
    model = Nesting
    fk_name = 'child'
    formset = ProtoStepSet
    form = ProtoStepForm
    verbose_name_plural = 'Parent Proto Steps'
    extra = 3

class NestingInline(admin.TabularInline):
    model = Nesting
    fk_name = 'parent'
    verbose_name_plural = 'Children'
    extra = 0

class ProtoTrackerAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links
    # parent inlines, child inlines
    inlines = [TrackerNestingInline, NestingInline]
    fieldsets = (
            (None, {'fields': ('summary', 'suffix', 'clone_per_locale')}),
    )

class ProtoTaskAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links
    # parent inlines, child inlines
    inlines = [TrackerNestingInline, NestingInline]
    fieldsets = (
            (None, {'fields': ('summary', 'suffix')}),
    )

class ProtoStepAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links + ('owner', 'is_review')
    # parent inlines, parent inlines, child inlines
    inlines = [TaskNestingInline, StepNestingInline, NestingInline]
    fieldsets = (
            (None, {'fields': ('summary', 'owner', 'is_review',
                               'allowed_time', 'clone_per_project')}),
    )
