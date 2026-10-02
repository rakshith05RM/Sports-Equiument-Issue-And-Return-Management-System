"""
Authentication module: login, logout, registration, session management.

Registration is intentionally closed-loop: anyone can request an account,
but new accounts are created with is_active = 0 and role = 'Staff'. They
cannot sign in until an Admin approves them from the Team screen
(routes/team.py). This mirrors how real operations software is provisioned
— nobody grants themselves elevated access by filling out a form.
"""

import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username_or_email = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username_or_email or not password:
            flash("Enter both a username/email and a password.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT user_id, username, email, password_hash, full_name, role, is_active
                       FROM users
                       WHERE (username = %s OR email = %s)""",
                    (username_or_email, username_or_email),
                )
                user = cursor.fetchone()
        finally:
            conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid login credentials.", "danger")
            return render_template("login.html")

        if not user["is_active"]:
            flash(
                "This account is awaiting administrator approval. You'll be able to sign in once it's approved.",
                "warning",
            )
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        flash(f"Welcome back, {user['full_name']}.", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        elif not re.match(r"^[a-zA-Z0-9_.]+$", username):
            errors.append("Username can only contain letters, numbers, dots, and underscores.")
        if not email or not EMAIL_RE.match(email):
            errors.append("Enter a valid email address.")
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("register.html", form=request.form)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id FROM users WHERE username = %s OR email = %s",
                    (username, email),
                )
                if cursor.fetchone():
                    flash("That username or email is already registered.", "danger")
                    return render_template("register.html", form=request.form)

                # New accounts are Staff by default and inactive until an
                # Admin approves them. No self-service path to Admin.
                cursor.execute(
                    """INSERT INTO users (username, email, password_hash, full_name, role, is_active)
                       VALUES (%s, %s, %s, %s, 'Staff', 0)""",
                    (username, email, generate_password_hash(password), full_name),
                )
            conn.commit()
        finally:
            conn.close()

        flash(
            "Account request submitted. An administrator needs to approve it before you can sign in.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("register.html", form={})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "info")
    return redirect(url_for("auth.login"))
