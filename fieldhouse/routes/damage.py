"""
Damaged / lost equipment module.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, admin_required, parse_int, parse_float, current_user_id

damage_bp = Blueprint("damage", __name__, url_prefix="/damage")

STATUSES = ["Reported", "Investigating", "Repaired", "Replaced", "Written Off", "Resolved"]


@damage_bp.route("/")
@login_required
def list_damage():
    report_type = request.args.get("type", "").strip()
    status = request.args.get("status", "").strip()

    where_clauses = []
    params = []
    if report_type:
        where_clauses.append("d.report_type = %s")
        params.append(report_type)
    if status:
        where_clauses.append("d.status = %s")
        params.append(status)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT d.*, e.equipment_name, m.full_name AS member_name
                FROM damage_reports d
                JOIN equipment e ON e.equipment_id = d.equipment_id
                LEFT JOIN members m ON m.member_id = d.member_id
                {where_sql}
                ORDER BY d.report_date DESC
            """, params)
            reports = cursor.fetchall()
    finally:
        conn.close()

    return render_template("damage/list.html", reports=reports, report_type=report_type,
                            status=status, statuses=STATUSES)


@damage_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_damage():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM equipment ORDER BY equipment_name")
            equipment_list = cursor.fetchall()
            cursor.execute("SELECT * FROM members ORDER BY full_name")
            members = cursor.fetchall()

        if request.method == "POST":
            equipment_id = parse_int(request.form.get("equipment_id"))
            member_id = parse_int(request.form.get("member_id")) or None
            report_type = request.form.get("report_type", "Damaged")
            quantity = parse_int(request.form.get("quantity"), 1)
            description = request.form.get("description", "").strip()
            estimated_cost = parse_float(request.form.get("estimated_cost"), 0)
            remarks = request.form.get("remarks", "").strip()

            errors = []
            if not equipment_id:
                errors.append("Please select equipment.")
            if quantity is None or quantity <= 0:
                errors.append("Quantity must be greater than zero.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("damage/add.html", equipment_list=equipment_list,
                                        members=members, form=request.form)

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO damage_reports
                    (equipment_id, member_id, report_type, quantity, description, estimated_cost,
                     status, remarks, reported_by)
                    VALUES (%s,%s,%s,%s,%s,%s,'Reported',%s,%s)
                """, (equipment_id, member_id, report_type, quantity, description, estimated_cost,
                      remarks, current_user_id()))

                if report_type == "Lost":
                    cursor.execute(
                        "UPDATE equipment SET status='Lost' WHERE equipment_id=%s", (equipment_id,)
                    )
                else:
                    cursor.execute(
                        "UPDATE equipment SET condition_status='Damaged' WHERE equipment_id=%s", (equipment_id,)
                    )
            conn.commit()
            flash("Report submitted successfully.", "success")
            return redirect(url_for("damage.list_damage"))
    finally:
        conn.close()

    return render_template("damage/add.html", equipment_list=equipment_list, members=members, form={})


@damage_bp.route("/edit/<int:report_id>", methods=["GET", "POST"])
@admin_required
def edit_damage(report_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM damage_reports WHERE report_id = %s", (report_id,))
            report = cursor.fetchone()

        if not report:
            flash("Report not found.", "danger")
            return redirect(url_for("damage.list_damage"))

        if request.method == "POST":
            status = request.form.get("status", "Reported")
            resolution = request.form.get("resolution", "").strip()
            remarks = request.form.get("remarks", "").strip()
            estimated_cost = parse_float(request.form.get("estimated_cost"), report["estimated_cost"])

            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE damage_reports SET status=%s, resolution=%s, remarks=%s, estimated_cost=%s
                    WHERE report_id=%s
                """, (status, resolution, remarks, estimated_cost, report_id))

                # If resolved via repair/replace, restore equipment to good condition
                if status in ("Repaired", "Replaced", "Resolved"):
                    cursor.execute(
                        "UPDATE equipment SET condition_status='Good' WHERE equipment_id=%s AND condition_status='Damaged'",
                        (report["equipment_id"],),
                    )
            conn.commit()
            flash("Report updated successfully.", "success")
            return redirect(url_for("damage.list_damage"))
    finally:
        conn.close()

    return render_template("damage/edit.html", report=report, statuses=STATUSES)
