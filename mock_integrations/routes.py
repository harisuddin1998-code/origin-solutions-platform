from flask import Blueprint, current_app, jsonify, request

from mock_integrations.helpers import create_fake_lead, first_tenant_id

bp = Blueprint("mock_integrations", __name__, template_folder="templates")


@bp.route("/mock/meta/leads", methods=["GET"])
def mock_meta_leads():
    """Stands in for the real Meta Ads Leads API - returns a freshly fabricated lead."""
    return jsonify(create_fake_lead(first_tenant_id(), "meta"))


@bp.route("/mock/tiktok/leads", methods=["GET"])
def mock_tiktok_leads():
    """Stands in for the real TikTok Ads Leads API."""
    return jsonify(create_fake_lead(first_tenant_id(), "tiktok"))


@bp.route("/mock/whatsapp/webhook", methods=["POST"])
def mock_whatsapp_webhook():
    """Stands in for a real WhatsApp Business API webhook receiving an inbound message."""
    token = request.headers.get("X-Webhook-Token") or (request.get_json(silent=True) or {}).get("token")
    if token != current_app.config["WHATSAPP_WEBHOOK_TOKEN"]:
        return jsonify({"error": "invalid webhook token"}), 401
    return jsonify(create_fake_lead(first_tenant_id(), "whatsapp"))
