"""
Shared helper functions and decorators used across route blueprints.
"""

from functools import wraps
from datetime import date
from flask import session, redirect, url_for, flash, request


def login_required(view_func):
    """Redirects to login page if no user is logged in."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    """Restricts a view to Admin role only. Must be used together with login_required
    (or after it) since it relies on session data set at login."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "Admin":
            flash("You do not have permission to access that page.", "danger")
            return redirect(url_for("dashboard.index"))
        return view_func(*args, **kwargs)
    return wrapped


def current_user_id():
    return session.get("user_id")


def current_role():
    return session.get("role")


def parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def today_str():
    return date.today().isoformat()
