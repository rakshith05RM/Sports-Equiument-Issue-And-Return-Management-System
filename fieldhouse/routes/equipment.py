"""
Equipment management module: add, edit, delete, view, search, filter, sort, paginate.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, admin_required, parse_int, parse_float
from config import Config

equipment_bp = Blueprint("equipment", __name__, url_prefix="/equipment")

CONDITIONS = ["New", "Good", "Fair", "Damaged", "Under Maintenance"]
STATUSES = ["Available", "Partially Available", "Issued", "Maintenance", "Lost"]

ALLOWED_SORT_COLUMNS = {
    "name": "e.equipment_name",
    "category": "c.category_name",
    "quantity": "e.total_quantity",
    "available": "e.available_quantity",
    "status": "e.status",
}


@equipment_bp.route("/")
@login_required
def list_equipment():
    search = request.args.get("search", "").strip()
    category_id = parse_int(request.args.get("category_id"))
    condition = request.args.get("condition", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "name")
    direction = request.args.get("dir", "asc")
    page = max(parse_int(request.args.get("page"), 1), 1)

    sort_col = ALLOWED_SORT_COLUMNS.get(sort, "e.equipment_name")
    direction_sql = "DESC" if direction == "desc" else "ASC"

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(e.equipment_name LIKE %s OR e.brand LIKE %s OR e.model LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])

    if category_id:
        where_clauses.append("e.category_id = %s")
        params.append(category_id)

    if condition:
        where_clauses.append("e.condition_status = %s")
        params.append(condition)

    if status:
        where_clauses.append("e.status = %s")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    per_page = Config.ITEMS_PER_PAGE
    offset = (page - 1) * per_page

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT COUNT(*) AS total FROM equipment e
                JOIN categories c ON c.category_id = e.category_id
                {where_sql}
            """, params)
            total_records = cursor.fetchone()["total"]

            cursor.execute(f"""
                SELECT e.*, c.category_name
                FROM equipment e
                JOIN categories c ON c.category_id = e.category_id
                {where_sql}
                ORDER BY {sort_col} {direction_sql}
                LIMIT %s OFFSET %s
            """, params + [per_page, offset])
            equipment_list = cursor.fetchall()

            cursor.execute("SELECT * FROM categories ORDER BY category_name")
            categories = cursor.fetchall()
    finally:
        conn.close()

    total_pages = max((total_records + per_page - 1) // per_page, 1)

    return render_template(
        "equipment/list.html",
        equipment_list=equipment_list,
        categories=categories,
        conditions=CONDITIONS,
        statuses=STATUSES,
        search=search,
        category_id=category_id,
        condition=condition,
        status=status,
        sort=sort,
        direction=direction,
        page=page,
        total_pages=total_pages,
        total_records=total_records,
    )


@equipment_bp.route("/view/<int:equipment_id>")
@login_required
def view_equipment(equipment_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, c.category_name FROM equipment e
                JOIN categories c ON c.category_id = e.category_id
                WHERE e.equipment_id = %s
            """, (equipment_id,))
            item = cursor.fetchone()

            if not item:
                flash("Equipment not found.", "danger")
                return redirect(url_for("equipment.list_equipment"))

            cursor.execute("""
                SELECT i.*, m.full_name AS member_name
                FROM equipment_issues i
                JOIN members m ON m.member_id = i.member_id
                WHERE i.equipment_id = %s
                ORDER BY i.issue_date DESC
                LIMIT 20
            """, (equipment_id,))
            issue_history = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM maintenance_records WHERE equipment_id = %s
                ORDER BY start_date DESC LIMIT 10
            """, (equipment_id,))
            maintenance_history = cursor.fetchall()
    finally:
        conn.close()

    return render_template(
        "equipment/view.html",
        item=item,
        issue_history=issue_history,
        maintenance_history=maintenance_history,
    )


@equipment_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_equipment():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY category_name")
            categories = cursor.fetchall()

        if request.method == "POST":
            name = request.form.get("equipment_name", "").strip()
            category_id = parse_int(request.form.get("category_id"))
            brand = request.form.get("brand", "").strip()
            model = request.form.get("model", "").strip()
            description = request.form.get("description", "").strip()
            total_quantity = parse_int(request.form.get("total_quantity"), 0)
            purchase_date = request.form.get("purchase_date") or None
            purchase_price = parse_float(request.form.get("purchase_price"), 0)
            condition_status = request.form.get("condition_status", "New")
            location = request.form.get("location", "").strip()
            supplier = request.form.get("supplier", "").strip()

            errors = []
            if not name:
                errors.append("Equipment name is required.")
            if not category_id:
                errors.append("Category is required.")
            if total_quantity is None or total_quantity < 0:
                errors.append("Total quantity cannot be negative.")
            if purchase_price is None or purchase_price < 0:
                errors.append("Purchase price cannot be negative.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("equipment/add.html", categories=categories,
                                        conditions=CONDITIONS, form=request.form)

            status = "Available" if total_quantity > 0 else "Maintenance"

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO equipment
                    (equipment_name, category_id, brand, model, description, total_quantity,
                     available_quantity, purchase_date, purchase_price, condition_status,
                     location, status, supplier)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (name, category_id, brand, model, description, total_quantity,
                      total_quantity, purchase_date, purchase_price, condition_status,
                      location, status, supplier))
            conn.commit()
            flash("Equipment added successfully.", "success")
            return redirect(url_for("equipment.list_equipment"))
    finally:
        conn.close()

    return render_template("equipment/add.html", categories=categories, conditions=CONDITIONS, form={})


@equipment_bp.route("/edit/<int:equipment_id>", methods=["GET", "POST"])
@admin_required
def edit_equipment(equipment_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY category_name")
            categories = cursor.fetchall()

            cursor.execute("SELECT * FROM equipment WHERE equipment_id = %s", (equipment_id,))
            item = cursor.fetchone()

        if not item:
            flash("Equipment not found.", "danger")
            return redirect(url_for("equipment.list_equipment"))

        if request.method == "POST":
            name = request.form.get("equipment_name", "").strip()
            category_id = parse_int(request.form.get("category_id"))
            brand = request.form.get("brand", "").strip()
            model = request.form.get("model", "").strip()
            description = request.form.get("description", "").strip()
            total_quantity = parse_int(request.form.get("total_quantity"), 0)
            purchase_date = request.form.get("purchase_date") or None
            purchase_price = parse_float(request.form.get("purchase_price"), 0)
            condition_status = request.form.get("condition_status", "New")
            location = request.form.get("location", "").strip()
            status = request.form.get("status", "Available")
            supplier = request.form.get("supplier", "").strip()

            issued_qty = item["total_quantity"] - item["available_quantity"]

            errors = []
            if not name:
                errors.append("Equipment name is required.")
            if not category_id:
                errors.append("Category is required.")
            if total_quantity is None or total_quantity < 0:
                errors.append("Total quantity cannot be negative.")
            if total_quantity is not None and total_quantity < issued_qty:
                errors.append(
                    f"Total quantity cannot be less than the currently issued quantity ({issued_qty})."
                )
            if purchase_price is None or purchase_price < 0:
                errors.append("Purchase price cannot be negative.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template("equipment/edit.html", item=item, categories=categories,
                                        conditions=CONDITIONS, statuses=STATUSES)

            new_available = total_quantity - issued_qty

            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE equipment SET
                        equipment_name=%s, category_id=%s, brand=%s, model=%s, description=%s,
                        total_quantity=%s, available_quantity=%s, purchase_date=%s, purchase_price=%s,
                        condition_status=%s, location=%s, status=%s, supplier=%s
                    WHERE equipment_id=%s
                """, (name, category_id, brand, model, description, total_quantity, new_available,
                      purchase_date, purchase_price, condition_status, location, status, supplier,
                      equipment_id))
            conn.commit()
            flash("Equipment updated successfully.", "success")
            return redirect(url_for("equipment.list_equipment"))
    finally:
        conn.close()

    return render_template("equipment/edit.html", item=item, categories=categories,
                            conditions=CONDITIONS, statuses=STATUSES)


@equipment_bp.route("/delete/<int:equipment_id>", methods=["POST"])
@admin_required
def delete_equipment(equipment_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS c FROM equipment_issues WHERE equipment_id = %s AND return_status IN ('Issued','Overdue','Partially Returned')",
                (equipment_id,),
            )
            active_issues = cursor.fetchone()["c"]

            if active_issues > 0:
                flash("Cannot delete equipment with active borrowings. Please wait until it is returned.", "danger")
                return redirect(url_for("equipment.list_equipment"))

            cursor.execute("DELETE FROM equipment WHERE equipment_id = %s", (equipment_id,))
        conn.commit()
        flash("Equipment deleted successfully.", "success")
    except Exception:
        conn.rollback()
        flash("Could not delete equipment. It may be referenced by other records.", "danger")
    finally:
        conn.close()

    return redirect(url_for("equipment.list_equipment"))
