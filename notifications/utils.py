from .models import Notification

def notify_user(recipient, title, message):
    """
    Utility function to create and queue in-app notifications for users.
    """
    try:
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message
        )
    except Exception as e:
        # Prevent database notifications failure from crashing the request thread
        print(f"Failed to create notification: {e}")
