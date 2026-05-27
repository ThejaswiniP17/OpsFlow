from django.contrib import admin
from .models import Task, Comment

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1

class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'team', 'assigned_to', 'status', 'priority', 'due_date']
    list_filter = ['status', 'priority', 'team']
    search_fields = ['title', 'description']
    inlines = [CommentInline]

admin.site.register(Task, TaskAdmin)
admin.site.register(Comment)
