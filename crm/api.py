from flask import g, jsonify, redirect, request, url_for

from core.auth import login_required
from crm.helpers import mark_all_read, unread_count


@login_required
def mark_all_read_view():
    mark_all_read(g.user["id"])
    return redirect(request.referrer or url_for("auth.login"))


@login_required
def unread_count_view():
    return jsonify({"unread_count": unread_count(g.user["id"])})


def register(app):
    app.add_url_rule(
        "/notifications/mark-all-read",
        endpoint="notifications_mark_all_read",
        view_func=mark_all_read_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/notifications/unread-count",
        endpoint="notifications_unread_count",
        view_func=unread_count_view,
        methods=["GET"],
    )
