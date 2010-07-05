from django.contrib import admin

from todo.models import *
from todo.admin.proto import (ProtoTrackerAdmin, ProtoTaskAdmin,
                              ProtoStepAdmin)

admin.site.register(Actor)
admin.site.register(Tracker)
admin.site.register(Task)
admin.site.register(Step)
admin.site.register(ProtoTracker, ProtoTrackerAdmin)
admin.site.register(ProtoTask, ProtoTaskAdmin)
admin.site.register(ProtoStep, ProtoStepAdmin)
