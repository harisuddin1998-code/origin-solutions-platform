import csv
import io

from flask import Blueprint, Response, abort, g, jsonify, redirect, render_template, request, url_for

from blueprints.sales import lead_engine
from core.auth import guard_role
from core.db import execute, query
from crm.helpers import (
    create_contact,
    create_deal,
    create_invoice,
    create_notification,
    create_proposal,
    create_quotation,
    get_or_create_company,
    record_payment,
    update_deal_stage,
)
from mock_integrations.helpers import first_tenant_id

MAX_IMPORT_ROWS = 5000

bp = Blueprint("sales", __name__, template_folder="templates", url_prefix="/sales")
bp.before_request(guard_role("sales", "super_admin"))

STATUSES = ["New", "Contacted", "Demo Scheduled", "Converted", "Lost"]
DEAL_STAGES = ["qualified", "proposal_sent", "negotiation", "won", "lost"]
TASK_STATUSES = ["todo", "in_progress", "done"]


@bp.route("/")
def index():
    return redirect(url_for("sales.dashboard"))


@bp.route("/dashboard")
def dashboard():
    rows = query("SELECT status, COUNT(*) AS total FROM leads GROUP BY status")
    funnel = {s: 0 for s in STATUSES}
    for r in rows:
        funnel[r["status"]] = r["total"]
    return render_template("sales/dashboard.html", funnel=funnel, statuses=STATUSES)


@bp.route("/leads")
def leads():
    rows = query(
        """
        SELECT l.*, t.name AS tenant_name, u.name AS assigned_name
        FROM leads l
        JOIN tenants t ON t.id = l.tenant_id
        LEFT JOIN users u ON u.id = l.assigned_to
        ORDER BY l.created_at DESC
        """
    )
    return render_template("sales/leads.html", leads=rows, statuses=STATUSES)


@bp.route("/leads/<int:lead_id>/status", methods=["POST"])
def update_lead_status(lead_id):
    status = request.form.get("status")
    if status not in STATUSES:
        abort(400)
    execute("UPDATE leads SET status = %s WHERE id = %s", (status, lead_id))
    return redirect(url_for("sales.leads"))


@bp.route("/leads/import", methods=["GET"])
def leads_import_form():
    return render_template("sales/leads_import.html")


@bp.route("/leads/import", methods=["POST"])
def leads_import():
    file = request.files.get("file")
    if not file or not file.filename:
        abort(400)
    if not file.filename.lower().endswith(".csv"):
        return render_template("sales/leads_import.html", error="Please upload a .csv file.")

    tenant_id = first_tenant_id()
    text = file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    valid_sources = {"meta", "tiktok", "whatsapp", "manual"}

    imported, skipped = [], []
    for i, row in enumerate(reader, start=2):
        if i - 1 > MAX_IMPORT_ROWS:
            skipped.append({"row": i, "reason": f"Import capped at {MAX_IMPORT_ROWS} rows."})
            break

        name = (row.get("name") or "").strip()
        phone = (row.get("phone") or "").strip()
        if not name or not phone:
            skipped.append({"row": i, "reason": "Missing name or phone."})
            continue

        source = (row.get("source") or "manual").strip().lower()
        if source not in valid_sources:
            source = "manual"

        execute(
            "INSERT INTO leads (tenant_id, source, name, phone, message, status, assigned_to) "
            "VALUES (%s, %s, %s, %s, %s, 'New', %s)",
            (tenant_id, source, name, phone, (row.get("message") or "").strip(), g.user["id"]),
        )
        imported.append(name)

    return render_template("sales/leads_import.html", imported=imported, skipped=skipped, done=True)


@bp.route("/leads/<int:lead_id>/convert", methods=["POST"])
def convert_lead(lead_id):
    lead = query("SELECT * FROM leads WHERE id = %s", (lead_id,), fetchone=True)
    if not lead:
        abort(404)

    company_name = request.form.get("company_name", "").strip() or f"{lead['name']}'s Company"
    deal_name = request.form.get("deal_name", "").strip() or f"{company_name} - New Deal"
    amount = request.form.get("amount", type=float) or 0

    company = get_or_create_company(company_name)
    contact_id = create_contact(
        company["id"], lead["name"], phone=lead["phone"] or "", owner_id=g.user["id"], lead_id=lead_id
    )
    create_deal(company["id"], deal_name, amount=amount, contact_id=contact_id, owner_id=g.user["id"])
    execute("UPDATE leads SET status = 'Converted' WHERE id = %s", (lead_id,))
    return redirect(url_for("sales.deals"))


@bp.route("/companies")
def companies():
    rows = query(
        """
        SELECT c.*, t.subdomain AS tenant_subdomain,
               (SELECT COUNT(*) FROM deals d WHERE d.company_id = c.id) AS deal_count
        FROM companies c
        LEFT JOIN tenants t ON t.id = c.tenant_id
        ORDER BY c.created_at DESC
        """
    )
    return render_template("sales/companies.html", companies=rows)


@bp.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = query("SELECT * FROM companies WHERE id = %s", (company_id,), fetchone=True)
    if not company:
        abort(404)
    contacts = query("SELECT * FROM contacts WHERE company_id = %s ORDER BY created_at DESC", (company_id,))
    company_deals = query("SELECT * FROM deals WHERE company_id = %s ORDER BY created_at DESC", (company_id,))
    invoices = query("SELECT * FROM client_invoices WHERE company_id = %s ORDER BY created_at DESC", (company_id,))
    return render_template(
        "sales/company_detail.html",
        company=company,
        contacts=contacts,
        deals=company_deals,
        invoices=invoices,
    )


@bp.route("/deals")
def deals():
    rows = query(
        """
        SELECT d.*, c.name AS company_name, ct.name AS contact_name
        FROM deals d
        JOIN companies c ON c.id = d.company_id
        LEFT JOIN contacts ct ON ct.id = d.contact_id
        ORDER BY d.updated_at DESC
        """
    )
    return render_template("sales/deals.html", deals=rows, stages=DEAL_STAGES)


@bp.route("/deals/<int:deal_id>")
def deal_detail(deal_id):
    deal = query(
        """
        SELECT d.*, c.name AS company_name FROM deals d
        JOIN companies c ON c.id = d.company_id
        WHERE d.id = %s
        """,
        (deal_id,),
        fetchone=True,
    )
    if not deal:
        abort(404)
    proposals = query("SELECT * FROM proposals WHERE deal_id = %s ORDER BY created_at DESC", (deal_id,))
    quotations = query("SELECT * FROM quotations WHERE deal_id = %s ORDER BY created_at DESC", (deal_id,))
    invoices = query("SELECT * FROM client_invoices WHERE deal_id = %s ORDER BY created_at DESC", (deal_id,))
    return render_template(
        "sales/deal_detail.html",
        deal=deal,
        proposals=proposals,
        quotations=quotations,
        invoices=invoices,
        stages=DEAL_STAGES,
    )


@bp.route("/deals/<int:deal_id>/stage", methods=["POST"])
def update_deal_stage_route(deal_id):
    stage = request.form.get("stage")
    if stage not in DEAL_STAGES:
        abort(400)
    lost_reason = request.form.get("lost_reason") if stage == "lost" else None
    result = update_deal_stage(deal_id, stage, lost_reason=lost_reason)
    if stage == "won" and result.get("new_login"):
        return redirect(url_for("sales.deal_detail", deal_id=deal_id, provisioned=1))
    return redirect(url_for("sales.deal_detail", deal_id=deal_id))


@bp.route("/deals/<int:deal_id>/forward", methods=["POST"])
def forward_to_admin(deal_id):
    deal = query(
        """
        SELECT d.*, c.name AS company_name, ct.name AS contact_name, ct.phone AS contact_phone
        FROM deals d
        JOIN companies c ON c.id = d.company_id
        LEFT JOIN contacts ct ON ct.id = d.contact_id
        WHERE d.id = %s
        """,
        (deal_id,),
        fetchone=True,
    )
    if not deal:
        abort(404)

    note = request.form.get("note", "").strip()
    message_parts = [f"Contact: {deal['contact_name'] or 'N/A'} ({deal['contact_phone'] or 'no phone'})"]
    if note:
        message_parts.append(note)

    admins = query("SELECT u.id FROM users u JOIN roles r ON r.id = u.role_id WHERE r.name = 'super_admin'")
    for admin in admins:
        create_notification(
            admin["id"],
            f"{g.user['name']} forwarded {deal['company_name']} — {deal['name']}",
            "\n".join(message_parts),
            url_for("super_admin.new_task"),
        )
    return redirect(url_for("sales.deal_detail", deal_id=deal_id, forwarded=1))


@bp.route("/deals/<int:deal_id>/proposal", methods=["POST"])
def add_proposal(deal_id):
    title = request.form.get("title", "").strip()
    if not title:
        abort(400)
    create_proposal(deal_id, title, request.form.get("content", ""))
    return redirect(url_for("sales.deal_detail", deal_id=deal_id))


@bp.route("/deals/<int:deal_id>/quotation", methods=["POST"])
def add_quotation(deal_id):
    total = request.form.get("total", type=float)
    description = request.form.get("description", "")
    if total is None:
        abort(400)
    create_quotation(deal_id, [{"description": description, "total": total}], total)
    return redirect(url_for("sales.deal_detail", deal_id=deal_id))


@bp.route("/deals/<int:deal_id>/invoice", methods=["POST"])
def add_invoice(deal_id):
    deal = query("SELECT * FROM deals WHERE id = %s", (deal_id,), fetchone=True)
    if not deal:
        abort(404)
    total = request.form.get("total", type=float)
    if total is None:
        abort(400)
    create_invoice(deal["company_id"], total, deal_id=deal_id, due_date=request.form.get("due_date") or None)
    return redirect(url_for("sales.deal_detail", deal_id=deal_id))


@bp.route("/invoices/<int:invoice_id>/pay", methods=["POST"])
def pay_invoice(invoice_id):
    invoice = query("SELECT * FROM client_invoices WHERE id = %s", (invoice_id,), fetchone=True)
    if not invoice:
        abort(404)
    record_payment(invoice_id, invoice["total"])
    return redirect(request.referrer or url_for("sales.deals"))


@bp.route("/tasks")
def tasks():
    rows = query(
        """
        SELECT t.*, ub.name AS assigner_name
        FROM tasks t
        LEFT JOIN users ub ON ub.id = t.assigned_by
        WHERE t.assigned_to = %s
        ORDER BY t.created_at DESC
        """,
        (g.user["id"],),
    )
    return render_template("sales/tasks.html", tasks=rows, columns=TASK_STATUSES)


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    status = request.form.get("status")
    if status not in TASK_STATUSES:
        abort(400)
    execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    return redirect(url_for("sales.tasks"))


# ============================================================
# LEAD GENERATION (multi-source business lead scraper)
# ============================================================
@bp.route("/lead-generation")
def lead_generation():
    return render_template("sales/lead_generation.html")


@bp.route("/lead-generation/api/search", methods=["POST"])
def lead_generation_search():
    status, body = lead_engine.execute_search(
        city=request.args.get("city", ""),
        country=request.args.get("country", ""),
        keywords=request.args.get("keywords", ""),
        num_leads=request.args.get("num_leads", 50, type=int) or 50,
        use_places=request.args.get("use_places", "false"),
        api_key=request.args.get("api_key", ""),
    )
    return jsonify(body), status


@bp.route("/lead-generation/api/leads")
def lead_generation_leads():
    return jsonify({"leads": lead_engine.all_leads, "total": len(lead_engine.all_leads)})


@bp.route("/lead-generation/api/stats")
def lead_generation_stats():
    return jsonify(lead_engine.get_stats())


@bp.route("/lead-generation/api/history")
def lead_generation_history():
    return jsonify({"history": lead_engine.search_history})


@bp.route("/lead-generation/api/logs")
def lead_generation_logs():
    return jsonify({"logs": lead_engine.search_logs})


@bp.route("/lead-generation/api/export")
def lead_generation_export_csv():
    content = lead_engine.export_csv_content()
    if content is None:
        return Response("No leads to export.", status=400)
    timestamp = lead_engine.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_export_{timestamp}.csv"},
    )


@bp.route("/lead-generation/api/export/excel")
def lead_generation_export_excel():
    content = lead_engine.export_excel_content()
    if content is None:
        return Response("No leads to export", status=400)
    timestamp = lead_engine.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=leads_export_{timestamp}.xlsx"},
    )
