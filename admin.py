from django.contrib import admin
from todo.models import Project, Batch, Todo

class BatchInline(admin.TabularInline):
    model = Batch
    prepopulated_fields = {'slug': ('name',)}
    verbose_name_plural = 'Batches'
    extra = 3

class ProjectAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('name', 'status', 'type')
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
    list_editable = ('summary', 'status', 'resolution', 'owner', 'order', 'is_auto_activated', 'is_review', '_has_children', 'resolves_parent', 'locale', 'project')
    list_display = list_display_links + list_editable + ('prototype', 'task', 'parent',)
    fieldsets = [
        (None, {'fields': ['prototype', 'summary', 'owner', 'status', 'resolution', 'task', 'parent', 'order', 'is_auto_activated', 'is_review', 'resolves_parent', 'locale', 'project']}),
    ]
    inlines = (TodoInline,)

admin.site.register(Project, ProjectAdmin)
admin.site.register(Todo, TodoAdmin)