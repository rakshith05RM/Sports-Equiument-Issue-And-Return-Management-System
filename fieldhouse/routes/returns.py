"""
Equipment return module. Uses a database transaction so inventory,
issue status, and (optionally) a damage record all update together.
"""

from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, parse_int, current_user_id

returns_bp = Blueprint("returns", __name__, url_prefix="/returns")


@returns_bp.route("/")
@login_required
def list_returns():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.*, i.equipment_id, i.member_id, e.equipment_name, m.full_name AS member_name
                FROM equipment_returns r
                JOIN equipment_issues i ON i.issue_id = r.issue_id
                JOIN equipment e ON e.equipment_id = i.equipment_id
                JOIN members m ON m.member_id = i.member_id
                ORDER BY r.return_date DESC
            """)
            returns = cursor.fetchall()
    finally:
        conn.close()

    return render_template("returns/list.html", returns=returns)


@returns_bp.route("/pending")
@login_required
def pending_returns():
    """Lists issues that are not yet fully returned, so staff can pick one to return."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT i.*, m.full_name AS member_name, e.equipment_name,
                       CASE WHEN i.expected_return_date < CURDATE() THEN 1 ELSE 0 END AS is_overdue
                FROM equipment_issues i
                JOIN members m ON m.member_id = i.member_id
                JOIN equipment e ON e.equipment_id = i.equipment_id
                WHERE i.return_status IN ('Issued','Partially Returned')
                ORDER BY i.expected_return_date ASC
            """)
            pending = cursor.fetchall()
    finally:
        conn.close()

    return render_template("returns/pending.html", pending=pending)


@returns_bp.route("/add/<int:issue_id>", methods=["GET", "POST"])
@login_required
def add_return(issue_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT i.*, e.equipment_name, m.full_name AS member_name
                FROM equipment_issues i
                JOIN equipment e ON e.equipment_id = i.equipment_id
                JOIN members m ON m.member_id = i.member_id
                WHERE i.issue_id = %s
            """, (issue_id,))
            issue = cursor.fetchone()

        if not issue:
            flash("Issue record not found.", "danger")
            return redirect(url_for("returns.pending_returns"))

        if issue["return_status"] not in ("Issued", "Partially Returned"):
            flash("This equipment has already been fully returned.", "warning")
            return redirect(url_for("returns.pending_returns"))

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(returned_quantity),0) AS returned FROM equipment_returns WHERE issue_id = %s",
                (issue_id,),
            )
            already_returned = cursor.fetchone()["returned"]

        remaining = issue["quantity"] - already_returned

        if request.method == "POST":
            returned_quantity = parse_int(request.form.get("returned_quantity"), 0)
            condition_after = request.form.get("condition_after_return", "").strip()
            is_damaged = request.form.get("is_damaged") == "on"
            is_lost = request.form.get("is_lost") == "on"
            remarks = request.form.get("remarks", "").strip()
            damage_description = request.form.get("damage_description", "").strip()
            estimated_cost = request.form.get("estimated_cost") or 0

            errors = []
            if not returned_quantity or returned_quantity <= 0:
                errors.append("Returned quantity must be greater than zero.")
            elif returned_quantity > remaining:
                errors.append(f"Returned quantity cannot exceed the outstanding quantity ({remaining}).")
            if not condition_after:
                errors.append("Please record the equipment's condition after return.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("returns/add.html", issue=issue, remaining=remaining)

            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO equipment_returns (issue_id, returned_quantity, return_date, "
                        "condition_after_return, is_damaged, remarks, received_by) "
                        "VALUES (%s,%s,CURDATE(),%s,%s,%s,%s)",
                        (issue_id, returned_quantity, condition_after, 1 if is_damaged else 0,
                         remarks, current_user_id()),
                    )

                    new_total_returned = already_returned + returned_quantity
                    if is_lost:
                        new_status = "Lost"
                    elif is_damaged:
                        new_status = "Damaged"
                    elif new_total_returned >= issue["quantity"]:
                        new_status = "Returned"
                    else:
                        new_status = "Partially Returned"

                    actual_return_date = date.today().isoformat() if new_status in (
                        "Returned", "Damaged", "Lost"
                    ) else issue["actual_return_date"]

                    cursor.execute(
                        "UPDATE equipment_issues SET return_status=%s, condition_after_return=%s, "
                        "actual_return_date=%s WHERE issue_id=%s",
                        (new_status, condition_after, actual_return_date, issue_id),
                    )

                    # Increase available quantity only for non-lost, non-damaged units
                    qty_back_to_stock = returned_quantity if not (is_damaged or is_lost) else 0
                    if qty_back_to_stock > 0:
                        cursor.execute(
                            "UPDATE equipment SET available_quantity = available_quantity + %s WHERE equipment_id = %s",
                            (qty_back_to_stock, issue["equipment_id"]),
                        )

                    # Refresh equipment status/condition
                    cursor.execute(
                        "SELECT total_quantity, available_quantity FROM equipment WHERE equipment_id = %s",
                        (issue["equipment_id"],),
                    )
                    eq = cursor.fetchone()
                    if eq["available_quantity"] >= eq["total_quantity"]:
                        eq_status = "Available"
                    elif eq["available_quantity"] > 0:
                        eq_status = "Partially Available"
                    else:
                        eq_status = "Issued"

                    if is_damaged:
                        cursor.execute(
                            "UPDATE equipment SET status=%s, condition_status='Damaged' WHERE equipment_id=%s",
                            (eq_status, issue["equipment_id"]),
                        )
                        cursor.execute("""
                            INSERT INTO damage_reports
                            (equipment_id, member_id, issue_id, report_type, quantity, description,
                             estimated_cost, status, reported_by)
                            VALUES (%s,%s,%s,'Damaged',%s,%s,%s,'Reported',%s)
                        """, (issue["equipment_id"], issue["member_id"], issue_id, returned_quantity,
                              damage_description or "Reported damaged on return.", estimated_cost,
                              current_user_id()))
                    elif is_lost:
                        cursor.execute(
                            "UPDATE equipment SET status='Lost' WHERE equipment_id=%s",
                            (issue["equipment_id"],),
                        )
                        cursor.execute("""
                            INSERT INTO damage_reports
                            (equipment_id, member_id, issue_id, report_type, quantity, description,
                             estimated_cost, status, reported_by)
                            VALUES (%s,%s,%s,'Lost',%s,%s,%s,'Reported',%s)
                        """, (issue["equipment_id"], issue["member_id"], issue_id, returned_quantity,
                              damage_description or "Reported lost on return.", estimated_cost,
                              current_user_id()))
                    else:
                        cursor.execute(
                            "UPDATE equipment SET status=%s WHERE equipment_id=%s",
                            (eq_status, issue["equipment_id"]),
                        )

                conn.commit()
                flash("Equipment returned successfully.", "success")
                return redirect(url_for("returns.pending_returns"))
            except Exception:
                conn.rollback()
                flash("Something went wrong while recording the return. Please try again.", "danger")
                return redirect(url_for("returns.add_return", issue_id=issue_id))
    finally:
        conn.close()

    return render_template("returns/add.html", issue=issue, remaining=remaining)
