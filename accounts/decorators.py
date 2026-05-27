from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def admin_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks if the user is logged in and is an Admin.
    """
    def check_admin(user):
        if user.is_authenticated and user.is_admin():
            return True
        raise PermissionDenied
    return user_passes_test(check_admin, login_url=login_url, redirect_field_name=redirect_field_name)(function)

def team_lead_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks if the user is logged in and is a Team Lead or Admin.
    """
    def check_team_lead(user):
        if user.is_authenticated and user.is_team_lead():
            return True
        raise PermissionDenied
    return user_passes_test(check_team_lead, login_url=login_url, redirect_field_name=redirect_field_name)(function)
