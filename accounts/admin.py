from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    list_filter = ['role', 'is_staff', 'is_superuser']
    
    # Expose custom fields in the Django admin UI
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Information', {'fields': ('role', 'bio', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Information', {'fields': ('role', 'bio', 'profile_picture')}),
    )

admin.site.register(User, CustomUserAdmin)
