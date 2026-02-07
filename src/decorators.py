from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_access_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def payment_reviewer_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)

        # SUPER sempre pode
        if getattr(current_user, "is_super", False):
            return fn(*args, **kwargs)

        # Quem tem flag de revisão pode
        if getattr(current_user, "can_review_payments", False):
            return fn(*args, **kwargs)

        abort(403)
    return wrapper


def super_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
