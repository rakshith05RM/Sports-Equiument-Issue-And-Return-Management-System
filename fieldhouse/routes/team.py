"""
Team module (Admin only): review pending registrations, approve or
deactivate accounts, and change roles. This is the only path by which a
user goes from 'registered' to 'can actually log in', and the only path
by which anyone becomes an Admin.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db_connection
from utils import admin_required, current_user_id

team_bp = Blueprint("team", __name__, url_prefix="/team")


@team_bp.route("/")
@admin_required
def list_users():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT user_id, username, email, full_name, role, is_active, created_at
                   FROM users ORDER BY is_active ASC, created_at DESC"""
            )
            users = cursor.fetchall()
    finally:
        conn.close()

    pending_count = sum(1 for u in users if not u["is_active"])
    return render_template("team/list.html", users=users, pending_count=pending_count)


@team_bp.route("/approve/<int:user_id>", methods=["POST"])
@admin_required
def approve_user(user_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET is_active = 1 WHERE user_id = %s", (user_id,))
        conn.commit()
        flash("Account approved. They can now sign in.", "success")
    finally:
        conn.close()
    return redirect(url_for("team.list_users"))


@team_bp.route("/deactivate/<int:user_id>", methods=["POST"])
@admin_required
def deactivate_user(user_id):
    if user_id == current_user_id():
        flash("You can't deactivate your own account.", "danger")
        return redirect(url_for("team.list_users"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET is_active = 0 WHERE user_id = %s", (user_id,))
        conn.commit()
        flash("Account deactivated. They will no longer be able to sign in.", "success")
    finally:
        conn.close()
    return redirect(url_for("team.list_users"))


@team_bp.route("/role/<int:user_id>", methods=["POST"])
@admin_required
def change_role(user_id):
    new_role = request.form.get("role")
    if new_role not in ("Admin", "Staff"):
        flash("Invalid role.", "danger")
        return redirect(url_for("team.list_users"))

    if user_id == current_user_id() and new_role != "Admin":
        flash("You can't remove your own Admin role.", "danger")
        return redirect(url_for("team.list_users"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (new_role, user_id))
        conn.commit()
        flash("Role updated.", "success")
    finally:
        conn.close()
    return redirect(url_for("team.list_users"))


@team_bp.route("/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id == current_user_id():
        flash("You can't delete your own account.", "danger")
        return redirect(url_for("team.list_users"))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS c FROM equipment_issues WHERE issued_by = %s", (user_id,)
            )
            linked = cursor.fetchone()["c"]
            if linked > 0:
                flash("This user has historical issue records and can't be deleted — deactivate them instead.", "danger")
                return redirect(url_for("team.list_users"))

            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        flash("Account deleted.", "success")
    finally:
        conn.close()
    return redirect(url_for("team.list_users"))
