from .models import ActivityLog

def log_activity(actor, action_type, description, task=None, team=None):
    """
    Utility function to log activities/actions in the system for auditing purposes.
    """
    try:
        ActivityLog.objects.create(
            actor=actor,
            action_type=action_type,
            description=description,
            task=task,
            team=team
        )
    except Exception as e:
        # Prevent logging errors from crashing the main request thread
        # In production, we'd log this error to standard output/logs (OpenTelemetry/Sentry)
        print(f"Failed to log activity: {e}")
