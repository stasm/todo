from django.contrib import admin
from todo.models import Actor, Project, Batch, Todo

class ActorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('name', 'slug')
    list_display = list_display_links + list_editable
    prepopulated_fields = {'slug': ('name',)}

class BatchInline(admin.TabularInline):
    model = Batch
    prepopulated_fields = {'slug': ('name',)}
    verbose_name_plural = 'Batches'
    extra = 3

class ProjectAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('name', 'slug', 'status', 'type')
    list_display = list_display_links + list_editable
    prepopulated_fields = {'slug': ('name',)}
    inlines = (BatchInline,)
    
class BatchAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('name', 'status')
    list_display = list_display_links + list_editable
    prepopulated_fields = {'slug': ('name',)}
    
class TodoInline(admin.TabularInline):
    model = Todo
    fk_name = 'parent'
    extra = 3
        
class TodoAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('summary', 'status', 'resolution', 'owner', 'order', 'snapshot_ts', 'is_auto_activated', 'is_review', '_has_children', 'resolves_parent', 'locale', 'project')
    list_display = list_display_links + list_editable + ('prototype', 'task', 'parent',)
    fieldsets = [
        (None, {
            'fields': ('summary', 'owner', 'status', 'resolution', 'prototype', 'task', 'parent', 'order'),
        }),
        ('Tasks only', {
            'classes': ('collapse',),
            'fields': ('locale', 'project', 'snapshot_ts', 'bug'),
        }),
        ('Flags', {
            'classes': ('collapse',),
            'fields': ('is_auto_activated', 'is_review', 'resolves_parent'),
        }),
    ]
    inlines = (TodoInline,)

admin.site.register(Actor, ActorAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Todo, TodoAdmin)