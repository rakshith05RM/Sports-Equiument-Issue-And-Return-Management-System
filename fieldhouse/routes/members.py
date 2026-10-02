"""
Member / student / player management module.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, admin_required, parse_int
from config import Config

members_bp = Blueprint("members", __name__, url_prefix="/members")


@members_bp.route("/")
@login_required
def list_members():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = max(parse_int(request.args.get("page"), 1), 1)
    per_page = Config.ITEMS_PER_PAGE
    offset = (page - 1) * per_page

    where_clauses = []
    params = []
    if search:
        where_clauses.append("(full_name LIKE %s OR student_code LIKE %s OR email LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if status:
        where_clauses.append("status = %s")
        params.append(status)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM members {where_sql}", params)
            total_records = cursor.fetchone()["total"]

            cursor.execute(
                f"SELECT * FROM members {where_sql} ORDER BY full_name LIMIT %s OFFSET %s",
                params + [per_page, offset],
            )
            members = cursor.fetchall()
    finally:
        conn.close()

    total_pages = max((total_records + per_page - 1) // per_page, 1)

    return render_template(
        "members/list.html",
        members=members,
        search=search,
        status=status,
        page=page,
        total_pages=total_pages,
        total_records=total_records,
    )


@members_bp.route("/view/<int:member_id>")
@login_required
def view_member(member_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM members WHERE member_id = %s", (member_id,))
            member = cursor.fetchone()

            if not member:
                flash("Member not found.", "danger")
                return redirect(url_for("members.list_members"))

            cursor.execute("""
                SELECT i.*, e.equipment_name
                FROM equipment_issues i
                JOIN equipment e ON e.equipment_id = i.equipment_id
                WHERE i.member_id = %s
                ORDER BY i.issue_date DESC
            """, (member_id,))
            borrow_history = cursor.fetchall()
    finally:
        conn.close()

    return render_template("members/view.html", member=member, borrow_history=borrow_history)


@members_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_member():
    if request.method == "POST":
        student_code = request.form.get("student_code", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender") or None
        dob = request.form.get("date_of_birth") or None
        department = request.form.get("department", "").strip()
        course_class = request.form.get("course_class", "").strip()
        address = request.form.get("address", "").strip()
        emergency_contact = request.form.get("emergency_contact", "").strip()
        status = request.form.get("status", "Active")

        errors = []
        if not student_code:
            errors.append("Student/Player ID is required.")
        if not full_name:
            errors.append("Full name is required.")

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT member_id FROM members WHERE student_code = %s", (student_code,))
                if cursor.fetchone():
                    errors.append("This Student/Player ID is already registered.")
                if email:
                    cursor.execute("SELECT member_id FROM members WHERE email = %s", (email,))
                    if cursor.fetchone():
                        errors.append("This email is already registered.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("members/add.html", form=request.form)

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO members
                    (student_code, full_name, email, phone, gender, date_of_birth, department,
                     course_class, address, emergency_contact, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (student_code, full_name, email or None, phone, gender, dob, department,
                      course_class, address, emergency_contact, status))
            conn.commit()
            flash("Member added successfully.", "success")
            return redirect(url_for("members.list_members"))
        finally:
            conn.close()

    return render_template("members/add.html", form={})


@members_bp.route("/edit/<int:member_id>", methods=["GET", "POST"])
@admin_required
def edit_member(member_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM members WHERE member_id = %s", (member_id,))
            member = cursor.fetchone()

        if not member:
            flash("Member not found.", "danger")
            return redirect(url_for("members.list_members"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            gender = request.form.get("gender") or None
            dob = request.form.get("date_of_birth") or None
            department = request.form.get("department", "").strip()
            course_class = request.form.get("course_class", "").strip()
            address = request.form.get("address", "").strip()
            emergency_contact = request.form.get("emergency_contact", "").strip()
            status = request.form.get("status", "Active")

            if not full_name:
                flash("Full name is required.", "danger")
                return render_template("members/edit.html", member=member)

            with conn.cursor() as cursor:
                if email:
                    cursor.execute("SELECT member_id FROM members WHERE email = %s AND member_id != %s",
                                    (email, member_id))
                    if cursor.fetchone():
                        flash("This email is already used by another member.", "danger")
                        return render_template("members/edit.html", member=member)

                cursor.execute("""
                    UPDATE members SET full_name=%s, email=%s, phone=%s, gender=%s, date_of_birth=%s,
                    department=%s, course_class=%s, address=%s, emergency_contact=%s, status=%s
                    WHERE member_id=%s
                """, (full_name, email or None, phone, gender, dob, department, course_class,
                      address, emergency_contact, status, member_id))
            conn.commit()
            flash("Member updated successfully.", "success")
            return redirect(url_for("members.list_members"))
    finally:
        conn.close()

    return render_template("members/edit.html", member=member)


@members_bp.route("/delete/<int:member_id>", methods=["POST"])
@admin_required
def delete_member(member_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS c FROM equipment_issues WHERE member_id = %s AND return_status IN ('Issued','Overdue','Partially Returned')",
                (member_id,),
            )
            active = cursor.fetchone()["c"]
            if active > 0:
                flash("Cannot delete member with active equipment borrowings.", "danger")
                return redirect(url_for("members.list_members"))

            cursor.execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        conn.commit()
        flash("Member deleted successfully.", "success")
    except Exception:
        conn.rollback()
        flash("Could not delete member. They may have historical records linked.", "danger")
    finally:
        conn.close()

    return redirect(url_for("members.list_members"))
