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
        if not current_user.is_authenticated or not current_user.can_review_payments:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def super_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
