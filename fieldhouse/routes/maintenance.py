"""
Equipment maintenance module.
Equipment under active maintenance is excluded from available inventory.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, admin_required, parse_int, parse_float, current_user_id

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")

STATUSES = ["Pending", "In Progress", "Completed", "Cancelled"]


@maintenance_bp.route("/")
@login_required
def list_maintenance():
    status = request.args.get("status", "").strip()
    where_sql = "WHERE mr.status = %s" if status else ""
    params = [status] if status else []

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT mr.*, e.equipment_name
                FROM maintenance_records mr
                JOIN equipment e ON e.equipment_id = mr.equipment_id
                {where_sql}
                ORDER BY mr.start_date DESC
            """, params)
            records = cursor.fetchall()
    finally:
        conn.close()

    return render_template("maintenance/list.html", records=records, status=status, statuses=STATUSES)


@maintenance_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_maintenance():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM equipment ORDER BY equipment_name")
            equipment_list = cursor.fetchall()

        if request.method == "POST":
            equipment_id = parse_int(request.form.get("equipment_id"))
            maintenance_type = request.form.get("maintenance_type", "").strip()
            problem_description = request.form.get("problem_description", "").strip()
            start_date = request.form.get("start_date")
            expected_completion_date = request.form.get("expected_completion_date") or None
            cost = parse_float(request.form.get("cost"), 0)
            technician_vendor = request.form.get("technician_vendor", "").strip()
            remarks = request.form.get("remarks", "").strip()
            take_out_of_service = request.form.get("take_out_of_service") == "on"
            quantity = parse_int(request.form.get("quantity"), 1)

            errors = []
            if not equipment_id:
                errors.append("Please select equipment.")
            if not start_date:
                errors.append("Start date is required.")
            if cost is None or cost < 0:
                errors.append("Cost cannot be negative.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("maintenance/add.html", equipment_list=equipment_list, form=request.form)

            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT available_quantity FROM equipment WHERE equipment_id = %s FOR UPDATE",
                        (equipment_id,),
                    )
                    eq = cursor.fetchone()

                    if take_out_of_service and quantity > eq["available_quantity"]:
                        conn.rollback()
                        flash("Cannot take more units out of service than are currently available.", "danger")
                        return render_template("maintenance/add.html", equipment_list=equipment_list, form=request.form)

                    cursor.execute("""
                        INSERT INTO maintenance_records
                        (equipment_id, maintenance_type, problem_description, start_date,
                         expected_completion_date, cost, technician_vendor, status, remarks, created_by)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'Pending',%s,%s)
                    """, (equipment_id, maintenance_type, problem_description, start_date,
                          expected_completion_date, cost, technician_vendor, remarks, current_user_id()))

                    if take_out_of_service:
                        new_available = eq["available_quantity"] - quantity
                        new_status = "Maintenance" if new_available == 0 else "Partially Available"
                        cursor.execute(
                            "UPDATE equipment SET available_quantity=%s, status=%s, "
                            "condition_status='Under Maintenance' WHERE equipment_id=%s",
                            (new_available, new_status, equipment_id),
                        )
                conn.commit()
                flash("Maintenance record added successfully.", "success")
                return redirect(url_for("maintenance.list_maintenance"))
            except Exception:
                conn.rollback()
                flash("Something went wrong while adding the maintenance record.", "danger")
                return redirect(url_for("maintenance.add_maintenance"))
    finally:
        conn.close()

    return render_template("maintenance/add.html", equipment_list=equipment_list, form={})


@maintenance_bp.route("/edit/<int:maintenance_id>", methods=["GET", "POST"])
@login_required
def edit_maintenance(maintenance_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM maintenance_records WHERE maintenance_id = %s", (maintenance_id,))
            record = cursor.fetchone()

        if not record:
            flash("Maintenance record not found.", "danger")
            return redirect(url_for("maintenance.list_maintenance"))

        if request.method == "POST":
            status = request.form.get("status", "Pending")
            actual_completion_date = request.form.get("actual_completion_date") or None
            cost = parse_float(request.form.get("cost"), record["cost"])
            remarks = request.form.get("remarks", "").strip()
            return_to_service = request.form.get("return_to_service") == "on"

            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE maintenance_records SET status=%s, actual_completion_date=%s, cost=%s, remarks=%s
                    WHERE maintenance_id=%s
                """, (status, actual_completion_date, cost, remarks, maintenance_id))

                if status == "Completed" and return_to_service:
                    cursor.execute(
                        "SELECT total_quantity, available_quantity FROM equipment WHERE equipment_id = %s FOR UPDATE",
                        (record["equipment_id"],),
                    )
                    eq = cursor.fetchone()
                    new_available = min(eq["available_quantity"] + 1, eq["total_quantity"])
                    new_status = "Available" if new_available >= eq["total_quantity"] else "Partially Available"
                    cursor.execute(
                        "UPDATE equipment SET available_quantity=%s, status=%s, condition_status='Good' "
                        "WHERE equipment_id=%s",
                        (new_available, new_status, record["equipment_id"]),
                    )
            conn.commit()
            flash("Maintenance record updated successfully.", "success")
            return redirect(url_for("maintenance.list_maintenance"))
    finally:
        conn.close()

    return render_template("maintenance/edit.html", record=record, statuses=STATUSES)
