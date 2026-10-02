"""
Dashboard module: statistics cards + Chart.js data, calculated live from MySQL.
"""

from flask import Blueprint, render_template
from database import get_db_connection
from utils import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ---- Core stat cards ----
            cursor.execute("SELECT COUNT(*) AS total FROM equipment")
            total_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COALESCE(SUM(available_quantity),0) AS total FROM equipment")
            available_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COALESCE(SUM(total_quantity - available_quantity),0) AS total FROM equipment")
            issued_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM equipment WHERE condition_status = 'Damaged'")
            damaged_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM equipment WHERE status = 'Lost'")
            lost_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM equipment WHERE condition_status = 'Under Maintenance'")
            maintenance_equipment = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) AS total FROM members")
            total_members = cursor.fetchone()["total"]

            cursor.execute(
                "SELECT COUNT(*) AS total FROM equipment_issues WHERE return_status IN ('Issued','Overdue','Partially Returned')"
            )
            active_borrowings = cursor.fetchone()["total"]

            cursor.execute(
                """SELECT COUNT(*) AS total FROM equipment_issues
                   WHERE expected_return_date < CURDATE()
                   AND return_status IN ('Issued','Partially Returned')"""
            )
            overdue_returns = cursor.fetchone()["total"]

            # ---- Chart: Equipment by category ----
            cursor.execute(
                """SELECT c.category_name, COUNT(e.equipment_id) AS count
                   FROM categories c
                   LEFT JOIN equipment e ON e.category_id = c.category_id
                   GROUP BY c.category_id, c.category_name
                   ORDER BY count DESC"""
            )
            category_rows = cursor.fetchall()

            # ---- Chart: Equipment availability (available vs issued) ----
            availability_data = {
                "available": available_equipment,
                "issued": issued_equipment,
            }

            # ---- Chart: Monthly issue/return statistics (last 6 months) ----
            cursor.execute(
                """SELECT DATE_FORMAT(issue_date, '%Y-%m') AS ym, COUNT(*) AS count
                   FROM equipment_issues
                   WHERE issue_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                   GROUP BY ym ORDER BY ym"""
            )
            monthly_issues = cursor.fetchall()

            cursor.execute(
                """SELECT DATE_FORMAT(return_date, '%Y-%m') AS ym, COUNT(*) AS count
                   FROM equipment_returns
                   WHERE return_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                   GROUP BY ym ORDER BY ym"""
            )
            monthly_returns = cursor.fetchall()

            # ---- Chart: Damaged/Lost statistics ----
            cursor.execute(
                "SELECT report_type, COUNT(*) AS count FROM damage_reports GROUP BY report_type"
            )
            damage_lost_rows = cursor.fetchall()

    finally:
        conn.close()

    stats = {
        "total_equipment": total_equipment,
        "available_equipment": available_equipment,
        "issued_equipment": issued_equipment,
        "damaged_equipment": damaged_equipment,
        "lost_equipment": lost_equipment,
        "maintenance_equipment": maintenance_equipment,
        "total_members": total_members,
        "active_borrowings": active_borrowings,
        "overdue_returns": overdue_returns,
    }

    charts = {
        "category_labels": [r["category_name"] for r in category_rows],
        "category_counts": [r["count"] for r in category_rows],
        "availability": availability_data,
        "monthly_labels": sorted(set([r["ym"] for r in monthly_issues] + [r["ym"] for r in monthly_returns])),
        "monthly_issues": {r["ym"]: r["count"] for r in monthly_issues},
        "monthly_returns": {r["ym"]: r["count"] for r in monthly_returns},
        "damage_lost_labels": [r["report_type"] for r in damage_lost_rows],
        "damage_lost_counts": [r["count"] for r in damage_lost_rows],
    }

    return render_template("dashboard.html", stats=stats, charts=charts)
