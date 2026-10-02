"""
Reports module: inventory, issued, returned, overdue, damaged, lost, maintenance,
member borrowing, and equipment usage reports — with CSV export.
"""

import csv
import io
from flask import Blueprint, render_template, request, Response
from database import get_db_connection
from utils import login_required

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

REPORT_TYPES = {
    "inventory": "Equipment Inventory Report",
    "available": "Available Equipment Report",
    "issued": "Issued Equipment Report",
    "returned": "Returned Equipment Report",
    "overdue": "Overdue Equipment Report",
    "damaged": "Damaged Equipment Report",
    "lost": "Lost Equipment Report",
    "maintenance": "Maintenance Report",
    "member_borrowing": "Member Borrowing Report",
    "usage": "Equipment Usage Report",
}


def _build_query(report_key, filters):
    """Returns (sql, params, headers) for the given report type and filters."""
    category_id = filters.get("category_id")
    status = filters.get("status")
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    member_id = filters.get("member_id")
    equipment_id = filters.get("equipment_id")

    if report_key == "inventory":
        sql = """SELECT e.equipment_id, e.equipment_name, c.category_name, e.total_quantity,
                         e.available_quantity, e.condition_status, e.status, e.location
                  FROM equipment e JOIN categories c ON c.category_id = e.category_id WHERE 1=1"""
        params = []
        if category_id:
            sql += " AND e.category_id = %s"; params.append(category_id)
        if status:
            sql += " AND e.status = %s"; params.append(status)
        sql += " ORDER BY e.equipment_name"
        headers = ["ID", "Equipment", "Category", "Total Qty", "Available Qty", "Condition", "Status", "Location"]
        return sql, params, headers

    if report_key == "available":
        sql = """SELECT e.equipment_id, e.equipment_name, c.category_name, e.available_quantity, e.location
                  FROM equipment e JOIN categories c ON c.category_id = e.category_id
                  WHERE e.available_quantity > 0"""
        params = []
        if category_id:
            sql += " AND e.category_id = %s"; params.append(category_id)
        sql += " ORDER BY e.equipment_name"
        headers = ["ID", "Equipment", "Category", "Available Qty", "Location"]
        return sql, params, headers

    if report_key in ("issued", "returned", "overdue"):
        sql = """SELECT i.issue_id, m.full_name AS member, e.equipment_name, i.quantity,
                         i.issue_date, i.expected_return_date, i.actual_return_date, i.return_status
                  FROM equipment_issues i
                  JOIN members m ON m.member_id = i.member_id
                  JOIN equipment e ON e.equipment_id = i.equipment_id
                  WHERE 1=1"""
        params = []
        if report_key == "issued":
            sql += " AND i.return_status IN ('Issued','Partially Returned')"
        elif report_key == "returned":
            sql += " AND i.return_status = 'Returned'"
        elif report_key == "overdue":
            sql += " AND i.expected_return_date < CURDATE() AND i.return_status IN ('Issued','Partially Returned')"
        if member_id:
            sql += " AND i.member_id = %s"; params.append(member_id)
        if equipment_id:
            sql += " AND i.equipment_id = %s"; params.append(equipment_id)
        if date_from:
            sql += " AND i.issue_date >= %s"; params.append(date_from)
        if date_to:
            sql += " AND i.issue_date <= %s"; params.append(date_to)
        sql += " ORDER BY i.issue_date DESC"
        headers = ["Issue ID", "Member", "Equipment", "Qty", "Issue Date", "Expected Return",
                   "Actual Return", "Status"]
        return sql, params, headers

    if report_key in ("damaged", "lost"):
        sql = """SELECT d.report_id, e.equipment_name, m.full_name AS member, d.quantity,
                         d.report_date, d.estimated_cost, d.status
                  FROM damage_reports d
                  JOIN equipment e ON e.equipment_id = d.equipment_id
                  LEFT JOIN members m ON m.member_id = d.member_id
                  WHERE d.report_type = %s"""
        params = ["Damaged" if report_key == "damaged" else "Lost"]
        if date_from:
            sql += " AND d.report_date >= %s"; params.append(date_from)
        if date_to:
            sql += " AND d.report_date <= %s"; params.append(date_to)
        sql += " ORDER BY d.report_date DESC"
        headers = ["Report ID", "Equipment", "Member", "Qty", "Report Date", "Est. Cost", "Status"]
        return sql, params, headers

    if report_key == "maintenance":
        sql = """SELECT mr.maintenance_id, e.equipment_name, mr.maintenance_type, mr.start_date,
                         mr.expected_completion_date, mr.actual_completion_date, mr.cost, mr.status
                  FROM maintenance_records mr JOIN equipment e ON e.equipment_id = mr.equipment_id
                  WHERE 1=1"""
        params = []
        if status:
            sql += " AND mr.status = %s"; params.append(status)
        if date_from:
            sql += " AND mr.start_date >= %s"; params.append(date_from)
        if date_to:
            sql += " AND mr.start_date <= %s"; params.append(date_to)
        sql += " ORDER BY mr.start_date DESC"
        headers = ["ID", "Equipment", "Type", "Start Date", "Expected Completion",
                   "Actual Completion", "Cost", "Status"]
        return sql, params, headers

    if report_key == "member_borrowing":
        sql = """SELECT m.full_name, m.student_code, COUNT(i.issue_id) AS total_borrowed,
                         SUM(CASE WHEN i.return_status IN ('Issued','Partially Returned') THEN 1 ELSE 0 END) AS active,
                         SUM(CASE WHEN i.expected_return_date < CURDATE() AND i.return_status IN ('Issued','Partially Returned') THEN 1 ELSE 0 END) AS overdue
                  FROM members m LEFT JOIN equipment_issues i ON i.member_id = m.member_id
                  WHERE 1=1"""
        params = []
        if member_id:
            sql += " AND m.member_id = %s"; params.append(member_id)
        sql += " GROUP BY m.member_id, m.full_name, m.student_code ORDER BY total_borrowed DESC"
        headers = ["Member", "Student Code", "Total Borrowed", "Active", "Overdue"]
        return sql, params, headers

    if report_key == "usage":
        sql = """SELECT e.equipment_name, c.category_name, COUNT(i.issue_id) AS times_issued,
                         COALESCE(SUM(i.quantity),0) AS total_units_issued
                  FROM equipment e
                  JOIN categories c ON c.category_id = e.category_id
                  LEFT JOIN equipment_issues i ON i.equipment_id = e.equipment_id
                  WHERE 1=1"""
        params = []
        if category_id:
            sql += " AND e.category_id = %s"; params.append(category_id)
        if date_from:
            sql += " AND (i.issue_date IS NULL OR i.issue_date >= %s)"; params.append(date_from)
        if date_to:
            sql += " AND (i.issue_date IS NULL OR i.issue_date <= %s)"; params.append(date_to)
        sql += " GROUP BY e.equipment_id, e.equipment_name, c.category_name ORDER BY times_issued DESC"
        headers = ["Equipment", "Category", "Times Issued", "Total Units Issued"]
        return sql, params, headers

    return None, None, None


@reports_bp.route("/")
@login_required
def index():
    report_key = request.args.get("report", "inventory")
    if report_key not in REPORT_TYPES:
        report_key = "inventory"

    filters = {
        "category_id": request.args.get("category_id") or None,
        "status": request.args.get("status") or None,
        "date_from": request.args.get("date_from") or None,
        "date_to": request.args.get("date_to") or None,
        "member_id": request.args.get("member_id") or None,
        "equipment_id": request.args.get("equipment_id") or None,
    }

    sql, params, headers = _build_query(report_key, filters)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            cursor.execute("SELECT * FROM categories ORDER BY category_name")
            categories = cursor.fetchall()
            cursor.execute("SELECT member_id, full_name FROM members ORDER BY full_name")
            members = cursor.fetchall()
            cursor.execute("SELECT equipment_id, equipment_name FROM equipment ORDER BY equipment_name")
            equipment_options = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "reports/index.html",
        report_key=report_key,
        report_types=REPORT_TYPES,
        headers=headers,
        rows=rows,
        categories=categories,
        members=members,
        equipment_options=equipment_options,
        filters=filters,
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    report_key = request.args.get("report", "inventory")
    if report_key not in REPORT_TYPES:
        report_key = "inventory"

    filters = {
        "category_id": request.args.get("category_id") or None,
        "status": request.args.get("status") or None,
        "date_from": request.args.get("date_from") or None,
        "date_to": request.args.get("date_to") or None,
        "member_id": request.args.get("member_id") or None,
        "equipment_id": request.args.get("equipment_id") or None,
    }

    sql, params, headers = _build_query(report_key, filters)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(list(row.values()))

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={report_key}_report.csv"
    return response
