from django.contrib import admin
from todo.models import Project, Todo

class ProjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    
class TodoInline(admin.TabularInline):
    model = Todo
    extra = 3
        
class TodoAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('summary', 'status', 'resolution', 'owner', 'order', 'is_auto_activated', 'is_review', 'resolves_parent', 'locale', 'project')
    list_display = list_display_links + list_editable + ('prototype', 'parent',)
    fieldsets = [
        (None, {'fields': ['prototype', 'summary', 'owner', 'status', 'resolution', 'parent', 'order', 'is_auto_activated', 'is_review', 'resolves_parent']}),
    ]
    inlines = (TodoInline,)

admin.site.register(Project, ProjectAdmin)
admin.site.register(Todo, TodoAdmin)