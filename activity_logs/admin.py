from django.contrib import admin
from .models import ActivityLog

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['actor', 'action_type', 'timestamp', 'description']
    list_filter = ['action_type', 'timestamp']
    search_fields = ['description', 'actor__username']

admin.site.register(ActivityLog, ActivityLogAdmin)
