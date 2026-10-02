"""
Equipment category management module.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from utils import login_required, admin_required

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")


@categories_bp.route("/")
@login_required
def list_categories():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT c.*, COUNT(e.equipment_id) AS equipment_count
                FROM categories c
                LEFT JOIN equipment e ON e.category_id = c.category_id
                GROUP BY c.category_id
                ORDER BY c.category_name
            """)
            categories = cursor.fetchall()
    finally:
        conn.close()
    return render_template("categories/list.html", categories=categories)


@categories_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_category():
    if request.method == "POST":
        name = request.form.get("category_name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Category name is required.", "danger")
            return render_template("categories/add.html", form=request.form)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (name,))
                if cursor.fetchone():
                    flash("A category with this name already exists.", "danger")
                    return render_template("categories/add.html", form=request.form)

                cursor.execute(
                    "INSERT INTO categories (category_name, description) VALUES (%s, %s)",
                    (name, description),
                )
            conn.commit()
            flash("Category added successfully.", "success")
            return redirect(url_for("categories.list_categories"))
        finally:
            conn.close()

    return render_template("categories/add.html", form={})


@categories_bp.route("/edit/<int:category_id>", methods=["GET", "POST"])
@admin_required
def edit_category(category_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
            category = cursor.fetchone()

        if not category:
            flash("Category not found.", "danger")
            return redirect(url_for("categories.list_categories"))

        if request.method == "POST":
            name = request.form.get("category_name", "").strip()
            description = request.form.get("description", "").strip()

            if not name:
                flash("Category name is required.", "danger")
                return render_template("categories/edit.html", category=category)

            with conn.cursor() as cursor:
                cursor.execute("SELECT category_id FROM categories WHERE category_name = %s AND category_id != %s",
                                (name, category_id))
                if cursor.fetchone():
                    flash("A category with this name already exists.", "danger")
                    return render_template("categories/edit.html", category=category)

                cursor.execute(
                    "UPDATE categories SET category_name=%s, description=%s WHERE category_id=%s",
                    (name, description, category_id),
                )
            conn.commit()
            flash("Category updated successfully.", "success")
            return redirect(url_for("categories.list_categories"))
    finally:
        conn.close()

    return render_template("categories/edit.html", category=category)


@categories_bp.route("/delete/<int:category_id>", methods=["POST"])
@admin_required
def delete_category(category_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS c FROM equipment WHERE category_id = %s", (category_id,))
            count = cursor.fetchone()["c"]

            if count > 0:
                flash(f"Cannot delete this category: {count} equipment item(s) still belong to it.", "danger")
                return redirect(url_for("categories.list_categories"))

            cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        conn.commit()
        flash("Category deleted successfully.", "success")
    finally:
        conn.close()

    return redirect(url_for("categories.list_categories"))
