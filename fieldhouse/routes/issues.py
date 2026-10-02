"""
Equipment issue (borrowing) module.
Handles the full issue workflow, including a confirmation step and an
atomic database transaction so inventory can never go inconsistent.
"""

from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import get_db_connection
from utils import login_required, parse_int, current_user_id

issues_bp = Blueprint("issues", __name__, url_prefix="/issues")


@issues_bp.route("/")
@login_required
def list_issues():
    status = request.args.get("status", "").strip()

    where_sql = ""
    params = []
    if status:
        where_sql = "WHERE i.return_status = %s"
        params.append(status)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT i.*, m.full_name AS member_name, m.student_code, e.equipment_name,
                       u.full_name AS issued_by_name,
                       CASE WHEN i.expected_return_date < CURDATE()
                                 AND i.return_status IN ('Issued','Partially Returned')
                            THEN 1 ELSE 0 END AS is_overdue
                FROM equipment_issues i
                JOIN members m ON m.member_id = i.member_id
                JOIN equipment e ON e.equipment_id = i.equipment_id
                JOIN users u ON u.user_id = i.issued_by
                {where_sql}
                ORDER BY i.issue_date DESC
            """, params)
            issues = cursor.fetchall()
    finally:
        conn.close()

    return render_template("issues/list.html", issues=issues, status=status)


@issues_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_issue():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM members WHERE status = 'Active' ORDER BY full_name")
            members = cursor.fetchall()
            cursor.execute("""
                SELECT * FROM equipment
                WHERE available_quantity > 0 AND status != 'Maintenance'
                ORDER BY equipment_name
            """)
            equipment_list = cursor.fetchall()

        if request.method == "POST":
            member_id = parse_int(request.form.get("member_id"))
            equipment_id = parse_int(request.form.get("equipment_id"))
            quantity = parse_int(request.form.get("quantity"), 0)
            expected_return_date = request.form.get("expected_return_date")
            condition_before = request.form.get("condition_before_issue", "").strip()
            remarks = request.form.get("remarks", "").strip()

            errors = []
            if not member_id:
                errors.append("Please select a member.")
            if not equipment_id:
                errors.append("Please select equipment.")
            if not quantity or quantity <= 0:
                errors.append("Quantity must be greater than zero.")
            if not expected_return_date:
                errors.append("Expected return date is required.")
            elif expected_return_date < date.today().isoformat():
                errors.append("Expected return date cannot be in the past.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("issues/add.html", members=members, equipment_list=equipment_list,
                                        form=request.form)

            # ---- Confirmation step: show summary before committing ----
            if request.form.get("confirmed") != "yes":
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM members WHERE member_id = %s", (member_id,))
                    member = cursor.fetchone()
                    cursor.execute("SELECT * FROM equipment WHERE equipment_id = %s", (equipment_id,))
                    eq = cursor.fetchone()

                if not member or not eq:
                    flash("Invalid member or equipment selected.", "danger")
                    return redirect(url_for("issues.add_issue"))

                if quantity > eq["available_quantity"]:
                    flash(
                        f"Insufficient equipment quantity. Only {eq['available_quantity']} available.",
                        "danger",
                    )
                    return render_template("issues/add.html", members=members, equipment_list=equipment_list,
                                            form=request.form)

                return render_template(
                    "issues/confirm.html",
                    member=member,
                    eq=eq,
                    quantity=quantity,
                    expected_return_date=expected_return_date,
                    condition_before=condition_before or eq["condition_status"],
                    remarks=remarks,
                )

            # ---- Final commit inside a transaction ----
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT available_quantity, condition_status FROM equipment WHERE equipment_id = %s FOR UPDATE",
                        (equipment_id,),
                    )
                    eq = cursor.fetchone()

                    if not eq or quantity > eq["available_quantity"]:
                        conn.rollback()
                        flash("Insufficient equipment quantity. Someone else may have just borrowed it.", "danger")
                        return redirect(url_for("issues.add_issue"))

                    cursor.execute("""
                        INSERT INTO equipment_issues
                        (member_id, equipment_id, quantity, issue_date, expected_return_date,
                         issued_by, return_status, condition_before_issue, remarks)
                        VALUES (%s,%s,%s,CURDATE(),%s,%s,'Issued',%s,%s)
                    """, (member_id, equipment_id, quantity, expected_return_date,
                          current_user_id(), condition_before or eq["condition_status"], remarks))

                    new_available = eq["available_quantity"] - quantity
                    new_status = "Available" if new_available == eq["available_quantity"] else (
                        "Partially Available" if new_available > 0 else "Issued"
                    )
                    cursor.execute(
                        "UPDATE equipment SET available_quantity = %s, status = %s WHERE equipment_id = %s",
                        (new_available, new_status, equipment_id),
                    )
                conn.commit()
                flash("Equipment issued successfully.", "success")
                return redirect(url_for("issues.list_issues"))
            except Exception:
                conn.rollback()
                flash("Something went wrong while issuing equipment. Please try again.", "danger")
                return redirect(url_for("issues.add_issue"))
    finally:
        conn.close()

    return render_template("issues/add.html", members=members, equipment_list=equipment_list, form={})


@issues_bp.route("/view/<int:issue_id>")
@login_required
def view_issue(issue_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT i.*, m.full_name AS member_name, m.student_code, m.phone,
                       e.equipment_name, u.full_name AS issued_by_name
                FROM equipment_issues i
                JOIN members m ON m.member_id = i.member_id
                JOIN equipment e ON e.equipment_id = i.equipment_id
                JOIN users u ON u.user_id = i.issued_by
                WHERE i.issue_id = %s
            """, (issue_id,))
            issue = cursor.fetchone()

            if not issue:
                flash("Issue record not found.", "danger")
                return redirect(url_for("issues.list_issues"))

            cursor.execute("SELECT * FROM equipment_returns WHERE issue_id = %s ORDER BY return_date", (issue_id,))
            returns = cursor.fetchall()
    finally:
        conn.close()

    return render_template("issues/view.html", issue=issue, returns=returns)
