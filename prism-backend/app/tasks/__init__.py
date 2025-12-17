"""
Celery Tasks Module
===================

This module ensures all Celery tasks are properly registered.
Importing this module will register all tasks with the Celery app.
"""
# Import tasks to ensure they're registered with Celery
try:
    from app.tasks import email_tasks  # noqa: F401
    __all__ = ["email_tasks"]
except ImportError:
    # Celery not available or tasks module has issues
    __all__ = []
