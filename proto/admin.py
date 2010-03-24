from django.contrib import admin

from todo.proto.models import Prototype, ProtoTask, Nesting

class PrototypeInline(admin.TabularInline):
    model = Nesting
    fk_name = "parent"
    verbose_name_plural = 'Sub proto steps'
    fields = ('order', 'child', 'is_auto_activated', 'resolves_parent', 'repeat_if_failed')
    extra = 3

class PrototypeAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('summary', 'owner', 'is_review')
    list_display = list_display_links + list_editable
    fieldsets = [
        (None, {'fields': ['summary', 'owner', 'is_review']}),
    ]
    inlines = (PrototypeInline,)
    
class ProtoTaskAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_editable = ('summary',)
    list_display = list_display_links + list_editable
    fieldsets = [
        (None, {'fields': ['summary']}),
    ]
    inlines = (PrototypeInline,)
    
class NestingAdmin(admin.ModelAdmin):
    list_display_links = ('__unicode__',)
    list_editable = ('parent', 'child', 'order', 'is_auto_activated', 'resolves_parent', 'repeat_if_failed')
    list_display = list_display_links + list_editable

admin.site.register(Prototype, PrototypeAdmin)
admin.site.register(ProtoTask, ProtoTaskAdmin)
admin.site.register(Nesting, NestingAdmin)
