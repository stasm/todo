from django.contrib import admin
from todo.models import Todo
    
class TodoInline(admin.TabularInline):
    model = Todo
    extra = 3
        
class TodoAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('summary', 'prototype', 'parent', 'status', 'owner', 'order', 'is_auto_activated', 'is_review', 'resolves_parent', 'repeat_if_failed')
    list_display = list_display_links + list_editable
    fieldsets = [
        (None, {'fields': ['prototype', 'summary', 'owner', 'status', 'parent', 'order', 'is_auto_activated', 'is_review', 'resolves_parent', 'repeat_if_failed']}),
    ]
    inlines = (TodoInline,)

admin.site.register(Todo, TodoAdmin)