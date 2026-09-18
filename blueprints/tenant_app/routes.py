from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from core.db import execute, query
from core.middleware import load_tenant_from_path

bp = Blueprint("tenant_app", __name__, template_folder="templates", url_prefix="/t/<tenant_subdomain>")
bp.before_request(load_tenant_from_path)


@bp.before_request
def _guard_tenant_access():
    if g.user is None:
        return redirect(url_for("auth.login", next=request.path))
    if g.user["role"] == "super_admin":
        return
    if g.user["role"] not in ("tenant_admin", "tenant_staff") or g.user["tenant_id"] != g.tenant["id"]:
        abort(403)


@bp.route("/")
def index():
    return redirect(url_for("tenant_app.dashboard", tenant_subdomain=g.tenant["subdomain"]))


@bp.route("/dashboard")
def dashboard():
    stats = {
        "inventory_items": query(
            "SELECT COUNT(*) AS total FROM inventory_items WHERE tenant_id = %s", (g.tenant["id"],), fetchone=True
        )["total"],
        "sales_today": query(
            """
            SELECT COUNT(*) AS total FROM pos_sales
            WHERE tenant_id = %s AND DATE(created_at) = CURDATE()
            """,
            (g.tenant["id"],),
            fetchone=True,
        )["total"],
        "active_vehicles": query(
            "SELECT COUNT(*) AS total FROM fleet_vehicles WHERE tenant_id = %s AND status = 'active'",
            (g.tenant["id"],),
            fetchone=True,
        )["total"],
    }
    return render_template("tenant_app/dashboard.html", stats=stats)


@bp.route("/pos", methods=["GET", "POST"])
def pos():
    if request.method == "POST":
        item_id = request.form.get("item_id", type=int)
        quantity = request.form.get("quantity", type=int) or 1
        item = query(
            "SELECT * FROM inventory_items WHERE id = %s AND tenant_id = %s", (item_id, g.tenant["id"]), fetchone=True
        )
        if not item:
            abort(400)
        total = float(item["price"]) * quantity
        execute(
            "INSERT INTO pos_sales (tenant_id, item_id, quantity, total, cashier_id) VALUES (%s, %s, %s, %s, %s)",
            (g.tenant["id"], item_id, quantity, total, g.user["id"]),
        )
        execute(
            "UPDATE inventory_items SET quantity = GREATEST(quantity - %s, 0) WHERE id = %s", (quantity, item_id)
        )
        return redirect(url_for("tenant_app.pos", tenant_subdomain=g.tenant["subdomain"]))

    items = query("SELECT * FROM inventory_items WHERE tenant_id = %s", (g.tenant["id"],))
    recent_sales = query(
        """
        SELECT s.*, i.name AS item_name FROM pos_sales s
        LEFT JOIN inventory_items i ON i.id = s.item_id
        WHERE s.tenant_id = %s ORDER BY s.created_at DESC LIMIT 10
        """,
        (g.tenant["id"],),
    )
    return render_template("tenant_app/pos.html", items=items, recent_sales=recent_sales)


@bp.route("/inventory", methods=["GET", "POST"])
def inventory():
    if request.method == "POST":
        execute(
            "INSERT INTO inventory_items (tenant_id, name, sku, quantity, price) VALUES (%s, %s, %s, %s, %s)",
            (
                g.tenant["id"],
                request.form.get("name"),
                request.form.get("sku"),
                request.form.get("quantity", type=int) or 0,
                request.form.get("price", type=float) or 0,
            ),
        )
        return redirect(url_for("tenant_app.inventory", tenant_subdomain=g.tenant["subdomain"]))

    items = query("SELECT * FROM inventory_items WHERE tenant_id = %s ORDER BY name", (g.tenant["id"],))
    return render_template("tenant_app/inventory.html", items=items)


@bp.route("/fleet", methods=["GET", "POST"])
def fleet():
    if request.method == "POST":
        execute(
            "INSERT INTO fleet_vehicles (tenant_id, name, plate_number, driver_name, status) VALUES (%s, %s, %s, %s, 'active')",
            (g.tenant["id"], request.form.get("name"), request.form.get("plate_number"), request.form.get("driver_name")),
        )
        return redirect(url_for("tenant_app.fleet", tenant_subdomain=g.tenant["subdomain"]))

    vehicles = query("SELECT * FROM fleet_vehicles WHERE tenant_id = %s ORDER BY name", (g.tenant["id"],))
    return render_template("tenant_app/fleet.html", vehicles=vehicles)
