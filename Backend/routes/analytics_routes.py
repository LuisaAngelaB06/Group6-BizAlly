from datetime import datetime
import csv
import io
import json
import zipfile
from xml.sax.saxutils import escape

from flask import Blueprint, jsonify, request, Response
from psycopg2 import errors
from psycopg2.extras import RealDictCursor

from Backend.database import get_connection
from Backend.routes.rbac import role_required


analytics_bp = Blueprint("analytics", __name__)

STATUS_LABELS = {
    1: "Open",
    2: "In Progress",
    3: "Resolved",
    4: "Closed",
}

CACHE = {}
CACHE_SECONDS = 45


def _json_error(message, status=500):
    return jsonify({"status": "error", "message": message, "error": message}), status


def _connection():
    conn = get_connection()
    if not conn:
        return None, None
    return conn, conn.cursor(cursor_factory=RealDictCursor)


def _now_ts():
    return datetime.utcnow().timestamp()


def _cache_key(name):
    return name, tuple(sorted(request.args.items()))


def _cached(name):
    key = _cache_key(name)
    item = CACHE.get(key)
    if item and _now_ts() - item["created"] < CACHE_SECONDS:
        return item["payload"]
    return None


def _store_cache(name, payload):
    CACHE[_cache_key(name)] = {"created": _now_ts(), "payload": payload}
    return payload


def _filters(alias="t", role_column=None):
    clauses = []
    params = []
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    role = request.args.get("role")
    status = request.args.get("status")
    priority = request.args.get("priority")
    service_type = request.args.get("service_type")
    technician = request.args.get("technician")
    customer = request.args.get("customer")

    if start_date:
        clauses.append(f"{alias}.date_created::date >= %s")
        params.append(start_date)
    if end_date:
        clauses.append(f"{alias}.date_created::date <= %s")
        params.append(end_date)
    if role and role_column:
        clauses.append(f"LOWER(COALESCE({role_column}, '')) = LOWER(%s)")
        params.append(role)
    if status:
        clauses.append(f"{alias}.status_id = %s")
        params.append(status)
    if priority:
        clauses.append(f"LOWER(COALESCE({alias}.priority, '')) = LOWER(%s)")
        params.append(priority)
    if service_type:
        clauses.append(f"{alias}.service_type_id = %s")
        params.append(service_type)
    if technician:
        clauses.append(f"{alias}.technician_id = %s")
        params.append(technician)
    if customer:
        clauses.append(f"{alias}.user_id = %s")
        params.append(customer)

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _login_filters(alias="lh"):
    clauses = []
    params = []
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    role = request.args.get("role")
    if start_date:
        clauses.append(f"{alias}.login_time::date >= %s")
        params.append(start_date)
    if end_date:
        clauses.append(f"{alias}.login_time::date <= %s")
        params.append(end_date)
    if role:
        clauses.append("LOWER(COALESCE(su.user_type, 'guest')) = LOWER(%s)")
        params.append(role)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _fetchall(cursor, query, params=None, fallback=None):
    try:
        cursor.execute(query, params or [])
        return cursor.fetchall()
    except errors.UndefinedTable:
        cursor.connection.rollback()
        return fallback if fallback is not None else []


def _fetchone(cursor, query, params=None, fallback=None):
    rows = _fetchall(cursor, query, params, [])
    return rows[0] if rows else (fallback or {})


def _count_map(rows, label_key="label", value_key="count"):
    return [{"label": str(row.get(label_key) or "Unspecified"), "value": int(row.get(value_key) or 0)} for row in rows]


def _ticket_base():
    return """
        FROM ticket t
        LEFT JOIN service_type st ON st.service_type_id = t.service_type_id
        LEFT JOIN technician tech ON tech.technician_id = t.technician_id
        LEFT JOIN "system_user" tech_user ON tech_user.user_id = tech.user_id
        LEFT JOIN "system_user" req_user ON req_user.user_id = t.user_id
        LEFT JOIN customer c ON c.customer_id = req_user.customer_id
    """


def _ticket_dataset(cursor, limit=50):
    where, params = _filters("t", role_column="req_user.user_type")
    cursor.execute(f"""
        SELECT
            t.ticket_id,
            t.concern_title,
            COALESCE(NULLIF(t.priority, ''), 'Medium') AS priority,
            t.status_id,
            COALESCE(st.name, 'Support') AS service_type,
            COALESCE(NULLIF(t.concern_type, ''), 'Other') AS concern_type,
            COALESCE(NULLIF(t.product_category, ''), 'Uncategorized') AS product_category,
            COALESCE(NULLIF(t.product_brand, ''), 'Unknown') AS product_brand,
            CONCAT_WS(' ', tech_user.first_name, tech_user.last_name) AS technician,
            CONCAT_WS(' ', req_user.first_name, req_user.last_name) AS customer,
            COALESCE(c.company_name, 'Individual') AS company,
            t.date_created,
            t.last_updated,
            ROUND(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0, 2) AS resolution_hours
        {_ticket_base()}
        {where}
        ORDER BY t.date_created DESC
        LIMIT %s
    """, params + [limit])
    return cursor.fetchall()


def _ticket_summary(cursor):
    where, params = _filters("t", role_column="req_user.user_type")
    summary = _fetchone(cursor, f"""
        SELECT
            COUNT(*)::int AS total,
            COUNT(*) FILTER (WHERE t.status_id = 1)::int AS open,
            COUNT(*) FILTER (WHERE t.status_id IN (3, 4))::int AS resolved,
            COUNT(*) FILTER (WHERE t.status_id = 4)::int AS closed,
            ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0)
                FILTER (WHERE t.status_id IN (3, 4)), 2) AS mttr_hours,
            COUNT(*) FILTER (
                WHERE t.status_id IN (3, 4)
                  AND t.last_updated <= t.date_created + INTERVAL '72 hours'
            )::int AS within_sla
        {_ticket_base()}
        {where}
    """, params, {})
    total = int(summary.get("total") or 0)
    resolved = int(summary.get("resolved") or 0)
    within_sla = int(summary.get("within_sla") or 0)
    summary["resolution_rate"] = round((resolved / total) * 100, 1) if total else 0
    summary["sla_compliance"] = round((within_sla / resolved) * 100, 1) if resolved else 0
    return summary


def _ticket_charts(cursor):
    where, params = _filters("t", role_column="req_user.user_type")
    trends = _fetchall(cursor, f"""
        SELECT TO_CHAR(DATE_TRUNC('day', t.date_created), 'YYYY-MM-DD') AS label,
               COUNT(*)::int AS opened,
               COUNT(*) FILTER (WHERE t.status_id IN (3, 4))::int AS resolved
        {_ticket_base()}
        {where}
        GROUP BY DATE_TRUNC('day', t.date_created)
        ORDER BY DATE_TRUNC('day', t.date_created)
    """, params)
    monthly = _fetchall(cursor, f"""
        SELECT TO_CHAR(DATE_TRUNC('month', t.date_created), 'Mon YYYY') AS label,
               COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY DATE_TRUNC('month', t.date_created)
        ORDER BY DATE_TRUNC('month', t.date_created)
    """, params)
    statuses = _fetchall(cursor, f"""
        SELECT t.status_id AS label, COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY t.status_id
        ORDER BY t.status_id
    """, params)
    priorities = _fetchall(cursor, f"""
        SELECT COALESCE(NULLIF(t.priority, ''), 'Medium') AS label, COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(NULLIF(t.priority, ''), 'Medium')
        ORDER BY count DESC
    """, params)
    concern_types = _fetchall(cursor, f"""
        SELECT COALESCE(NULLIF(t.concern_type, ''), 'Other') AS label, COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(NULLIF(t.concern_type, ''), 'Other')
        ORDER BY count DESC
        LIMIT 10
    """, params)
    categories = _fetchall(cursor, f"""
        SELECT COALESCE(NULLIF(t.product_category, ''), 'Uncategorized') AS label, COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(NULLIF(t.product_category, ''), 'Uncategorized')
        ORDER BY count DESC
        LIMIT 10
    """, params)
    brands = _fetchall(cursor, f"""
        SELECT COALESCE(NULLIF(t.product_brand, ''), 'Unknown') AS label, COUNT(*)::int AS count
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(NULLIF(t.product_brand, ''), 'Unknown')
        ORDER BY count DESC
        LIMIT 10
    """, params)
    return {
        "trends": [dict(row) for row in trends],
        "monthly_growth": _count_map(monthly),
        "statuses": [{"label": STATUS_LABELS.get(row.get("label"), str(row.get("label"))), "value": int(row.get("count") or 0)} for row in statuses],
        "priorities": _count_map(priorities),
        "concern_types": _count_map(concern_types),
        "product_categories": _count_map(categories),
        "product_brands": _count_map(brands),
    }


def _add_sla_rates(rows):
    rated = []
    for row in rows:
        row = dict(row)
        resolved = int(row.get("resolved") or 0)
        within_sla = int(row.get("within_sla") or 0)
        breaches = int(row.get("breaches") or 0)
        row["sla_compliance"] = round((within_sla / resolved) * 100, 1) if resolved else 0
        row["breach_rate"] = round((breaches / resolved) * 100, 1) if resolved else 0
        rated.append(row)
    return rated


def _sla_service_rows(cursor):
    where, params = _filters("t", role_column="req_user.user_type")
    rows = _fetchall(cursor, f"""
        SELECT
            COALESCE(st.name, 'Support') AS service_type,
            COUNT(t.ticket_id) FILTER (WHERE t.status_id IN (3, 4))::int AS resolved,
            COUNT(t.ticket_id) FILTER (
                WHERE t.status_id IN (3, 4)
                  AND t.last_updated <= t.date_created + INTERVAL '72 hours'
            )::int AS within_sla,
            COUNT(t.ticket_id) FILTER (
                WHERE t.status_id IN (3, 4)
                  AND t.last_updated > t.date_created + INTERVAL '72 hours'
            )::int AS breaches,
            ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0)
                FILTER (WHERE t.status_id IN (3, 4)), 2) AS avg_resolution_hours,
            ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0), 2) AS avg_response_hours
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(st.name, 'Support')
        ORDER BY resolved DESC
    """, params)
    return _add_sla_rates(rows)


def _sla_product_category_rows(cursor):
    where, params = _filters("t", role_column="req_user.user_type")
    rows = _fetchall(cursor, f"""
        SELECT
            COALESCE(NULLIF(t.product_category, ''), 'Uncategorized') AS product_category,
            COUNT(t.ticket_id) FILTER (WHERE t.status_id IN (3, 4))::int AS resolved,
            COUNT(t.ticket_id) FILTER (
                WHERE t.status_id IN (3, 4)
                  AND t.last_updated <= t.date_created + INTERVAL '72 hours'
            )::int AS within_sla,
            COUNT(t.ticket_id) FILTER (
                WHERE t.status_id IN (3, 4)
                  AND t.last_updated > t.date_created + INTERVAL '72 hours'
            )::int AS breaches,
            ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0)
                FILTER (WHERE t.status_id IN (3, 4)), 2) AS avg_resolution_hours
        {_ticket_base()}
        {where}
        GROUP BY COALESCE(NULLIF(t.product_category, ''), 'Uncategorized')
        ORDER BY resolved DESC
    """, params)
    return _add_sla_rates(rows)


HELPFUL_FEEDBACK = (
    'resolved', 'issue resolved', 'useful', 'helpful', 'yes', 'positive', 'satisfied'
)
NOT_HELPFUL_FEEDBACK = (
    'unresolved', 'still not resolved', 'not_helpful', 'not helpful', 'no', 'negative', 'unsatisfied'
)
NEUTRAL_FEEDBACK = (
    'partially_resolved', 'partially resolved', 'neutral', 'other', 'unknown', 'maybe'
)


def _normalize_feedback_rating(value):
    if not value:
        return 'Neutral'
    normalized = str(value).strip().lower()
    if normalized in HELPFUL_FEEDBACK:
        return 'Helpful'
    if normalized in NOT_HELPFUL_FEEDBACK:
        return 'Not Helpful'
    return 'Neutral'


def _quickfix_filter_clauses():
    clauses = []
    params = []
    date_from = request.args.get('date_from') or request.args.get('start_date')
    date_to = request.args.get('date_to') or request.args.get('end_date')
    source = request.args.get('source') or request.args.get('module')
    rating = request.args.get('rating')
    helpfulness = request.args.get('helpfulness')

    if date_from:
        clauses.append("created_at::date >= %s")
        params.append(date_from)
    if date_to:
        clauses.append("created_at::date <= %s")
        params.append(date_to)
    if source:
        clauses.append("LOWER(source) = LOWER(%s)")
        params.append(source)
    if rating:
        clauses.append("LOWER(rating) = LOWER(%s)")
        params.append(rating)
    if helpfulness:
        normalized = _normalize_feedback_rating(helpfulness)
        if normalized == 'Helpful':
            clauses.append(f"LOWER(rating) = ANY(ARRAY[{', '.join(['%s'] * len(HELPFUL_FEEDBACK))}])")
            params.extend(HELPFUL_FEEDBACK)
        elif normalized == 'Not Helpful':
            clauses.append(f"LOWER(rating) = ANY(ARRAY[{', '.join(['%s'] * len(NOT_HELPFUL_FEEDBACK))}])")
            params.extend(NOT_HELPFUL_FEEDBACK)
        else:
            clauses.append(f"LOWER(rating) NOT IN ({', '.join(['%s'] * (len(HELPFUL_FEEDBACK) + len(NOT_HELPFUL_FEEDBACK)))})")
            params.extend(HELPFUL_FEEDBACK + NOT_HELPFUL_FEEDBACK)

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _mask_session_id(value):
    if not value:
        return None
    session = str(value)
    return '••••' + session[-4:] if len(session) > 4 else '••••'


def _map_quickfix_row(row):
    created_at = row.get('created_at')
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        'feedback_id': int(row.get('feedback_id') or 0),
        'source': row.get('source') or 'Unknown',
        'rating': row.get('rating') or 'Unknown',
        'nickname': row.get('nickname') or 'Anonymous',
        'user_id': int(row.get('user_id')) if row.get('user_id') is not None else None,
        'session_id': _mask_session_id(row.get('session_id')),
        'created_at': created_at,
    }


def _quickfix_summary(cursor):
    where, params = _quickfix_filter_clauses()
    rating_groups = list(HELPFUL_FEEDBACK) + list(NOT_HELPFUL_FEEDBACK)
    summary_row = _fetchone(cursor, f"""
        SELECT
            COUNT(*)::int AS total,
            COUNT(*) FILTER (WHERE LOWER(rating) = ANY(ARRAY[{', '.join(['%s'] * len(HELPFUL_FEEDBACK))}]))::int AS helpful,
            COUNT(*) FILTER (WHERE LOWER(rating) = ANY(ARRAY[{', '.join(['%s'] * len(NOT_HELPFUL_FEEDBACK))}]))::int AS not_helpful,
            COUNT(*) FILTER (WHERE LOWER(rating) NOT IN ({', '.join(['%s'] * len(rating_groups))}) )::int AS neutral
        FROM system_feedback
        {where}
    """, params + list(HELPFUL_FEEDBACK) + list(NOT_HELPFUL_FEEDBACK) + rating_groups, {'total': 0, 'helpful': 0, 'not_helpful': 0, 'neutral': 0})

    total = int(summary_row.get('total') or 0)
    helpful = int(summary_row.get('helpful') or 0)
    not_helpful = int(summary_row.get('not_helpful') or 0)
    neutral = int(summary_row.get('neutral') or 0)
    rate = round((helpful / total) * 100, 1) if total else 0

    sources = [dict(row) for row in _fetchall(cursor, f"""
        SELECT source AS label, COUNT(*)::int AS value
        FROM system_feedback
        {where}
        GROUP BY source
        ORDER BY value DESC
        LIMIT 20
    """, params)]

    trend = [dict(row) for row in _fetchall(cursor, f"""
        SELECT TO_CHAR(created_at::date, 'YYYY-MM-DD') AS label, COUNT(*)::int AS value
        FROM system_feedback
        {where}
        GROUP BY created_at::date
        ORDER BY created_at::date
    """, params)]

    latest_rows = [dict(row) for row in _fetchall(cursor, f"""
        SELECT feedback_id, source, rating, nickname, user_id, session_id, created_at
        FROM system_feedback
        {where}
        ORDER BY created_at DESC
        LIMIT 20
    """, params)]

    return {
        'status': 'success',
        'summary': {
            'total_feedback': total,
            'helpful': helpful,
            'not_helpful': not_helpful,
            'neutral': neutral,
            'helpfulness_rate': rate,
        },
        'charts': {
            'helpfulness': [
                {'label': 'Helpful', 'value': helpful},
                {'label': 'Not Helpful', 'value': not_helpful},
                {'label': 'Neutral', 'value': neutral}
            ],
            'sources': sources,
            'trend': trend,
        },
        'table': [
            {
                **_map_quickfix_row(row),
                'linked_user': 'Linked User' if row.get('user_id') else 'Anonymous'
            } for row in latest_rows
        ]
    }


def _quickfix_list(cursor, page=1, per_page=25):
    where, params = _quickfix_filter_clauses()
    offset = max((page - 1) * per_page, 0)
    total = int(_fetchone(cursor, f"SELECT COUNT(*)::int AS total FROM system_feedback {where}", params, {'total': 0}).get('total') or 0)
    rows = [dict(row) for row in _fetchall(cursor, f"""
        SELECT feedback_id, source, rating, nickname, user_id, session_id, created_at
        FROM system_feedback
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])]

    return {
        'status': 'success',
        'summary': {
            'total_feedback': total,
        },
        'table': [
            {
                **_map_quickfix_row(row),
                'linked_user': 'Linked User' if row.get('user_id') else 'Anonymous'
            } for row in rows
        ],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total': total,
        }
    }


def _quickfix_report_rows(cursor):
    where, params = _quickfix_filter_clauses()
    rows = [dict(row) for row in _fetchall(cursor, f"""
        SELECT feedback_id, source, rating, nickname, user_id,
            CONCAT('••••', RIGHT(session_id, 4)) AS session_id, created_at
        FROM system_feedback
        {where}
        ORDER BY created_at DESC
        LIMIT 1000
    """, params)]
    return [
        {
            'feedback_id': int(row.get('feedback_id') or 0),
            'source': row.get('source') or 'Unknown',
            'rating': row.get('rating') or 'Unknown',
            'nickname': row.get('nickname') or 'Anonymous',
            'user_id': int(row.get('user_id')) if row.get('user_id') is not None else None,
            'session_id': row.get('session_id'),
            'created_at': row.get('created_at').isoformat() if isinstance(row.get('created_at'), datetime) else row.get('created_at')
        }
    for row in rows]


@analytics_bp.route("/analytics/quickfix-feedback/summary", methods=["GET"])
@role_required("admin")
def quickfix_feedback_summary():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        payload = _quickfix_summary(cursor)
        return jsonify(payload), 200
    except Exception as e:
        print(f"Quick Fix feedback analytics error: {e}")
        return _json_error("Failed to fetch Quick Fix feedback analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/quickfix-feedback/list", methods=["GET"])
@role_required("admin")
def quickfix_feedback_list():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        payload = _quickfix_list(cursor, page=page, per_page=per_page)
        return jsonify(payload), 200
    except Exception as e:
        print(f"Quick Fix feedback list error: {e}")
        return _json_error("Failed to fetch Quick Fix feedback list")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/quickfix-feedback/export", methods=["GET"])
@role_required("admin")
def quickfix_feedback_export():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        fmt = (request.args.get('format') or 'csv').lower()
        rows = _quickfix_report_rows(cursor)
        filename = f"AlliTrack_QuickFixFeedback_{datetime.utcnow().strftime('%Y%m%d')}"

        # 🌟 LOG THE DATA EXPORT
        from flask import g
        from Backend.routes.utils import log_system_event
        from Backend.routes.rbac import get_current_user
        current_user = getattr(g, "current_user", None) or get_current_user()
        admin_id = current_user.get("user_id") if current_user else "System"

        log_system_event(
            user_identifier=str(admin_id),
            category="Analytics & Reports",
            action="Data Exported",
            log_level="WARNING",
            description=f"Administrator exported Quick Fix Feedback data as {fmt.upper()}."
        )

        if fmt == 'xlsx':
            return _xlsx_response(rows, filename)
        if fmt == 'pdf':
            return _pdf_response(rows, filename)
        return _csv_response(rows, filename)
    except Exception as e:
        print(f"Quick Fix feedback export error: {e}")
        return _json_error("Failed to export Quick Fix feedback analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/tickets", methods=["GET"])
@role_required("admin")
def ticket_analytics():
    cached = _cached("tickets")
    if cached:
        return jsonify(cached), 200
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        payload = {
            "status": "success",
            "summary": _ticket_summary(cursor),
            "charts": _ticket_charts(cursor),
            "table": [dict(row) for row in _ticket_dataset(cursor)],
            "meta": {"cache_ttl_seconds": CACHE_SECONDS, "refresh_mode": "polling"},
        }
        return jsonify(_store_cache("tickets", payload)), 200
    except Exception as e:
        print(f"Ticket analytics error: {e}")
        return _json_error("Failed to fetch ticket analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/technicians", methods=["GET"])
@role_required("admin")
def technician_analytics():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        where, params = _filters("t", role_column="su.user_type")
        rows = _fetchall(cursor, f"""
            SELECT
                tech.technician_id,
                COALESCE(NULLIF(CONCAT_WS(' ', su.first_name, su.last_name), ''), su.email, 'Technician') AS name,
                COUNT(t.ticket_id)::int AS assigned,
                COUNT(t.ticket_id) FILTER (WHERE t.status_id IN (3, 4))::int AS resolved,
                COUNT(t.ticket_id) FILTER (WHERE t.status_id NOT IN (3, 4))::int AS pending,
                ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0)
                    FILTER (WHERE t.status_id IN (3, 4)), 2) AS avg_resolution_hours,
                COUNT(t.ticket_id) FILTER (
                    WHERE t.status_id IN (3, 4)
                      AND t.last_updated <= t.date_created + INTERVAL '72 hours'
                )::int AS within_sla,
                COALESCE(MODE() WITHIN GROUP (ORDER BY NULLIF(t.concern_type, '')), 'Other') AS common_concern
            FROM technician tech
            JOIN "system_user" su ON su.user_id = tech.user_id
            LEFT JOIN ticket t ON t.technician_id = tech.technician_id
            {where.replace(' WHERE ', ' WHERE ') if where else ''}
            GROUP BY tech.technician_id, su.first_name, su.last_name, su.email
            ORDER BY resolved DESC, assigned DESC
        """, params)
        leaderboard = []
        heatmap = []
        for row in rows:
            assigned = int(row.get("assigned") or 0)
            resolved = int(row.get("resolved") or 0)
            within_sla = int(row.get("within_sla") or 0)
            row = dict(row)
            row["sla_compliance"] = round((within_sla / resolved) * 100, 1) if resolved else 0
            row["performance_score"] = round((resolved * 0.55) + (row["sla_compliance"] * 0.35) + max(0, 10 - assigned) * 0.1, 1)
            leaderboard.append(row)
            heatmap.append({"label": row["name"], "value": assigned})
        performance_ranking = [{"label": r["name"], "value": r.get("performance_score") or 0} for r in leaderboard]
        return jsonify({
            "status": "success",
            "summary": {
                "technicians": len(rows),
                "assigned": sum(int(r.get("assigned") or 0) for r in rows),
                "resolved": sum(int(r.get("resolved") or 0) for r in rows),
                "pending": sum(int(r.get("pending") or 0) for r in rows),
            },
            "leaderboard": leaderboard,
            "charts": {
                "workload": heatmap,
                "performance_ranking": performance_ranking,
                "common_concerns": [{"label": r["name"], "value": r.get("common_concern") or "Other"} for r in leaderboard],
            },
            "table": leaderboard,
        }), 200
    except Exception as e:
        print(f"Technician analytics error: {e}")
        return _json_error("Failed to fetch technician analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/customers", methods=["GET"])
@role_required("admin")
def customer_analytics():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        where, params = _filters("t", role_column="req_user.user_type")
        rows = _fetchall(cursor, f"""
            SELECT
                req_user.user_id,
                COALESCE(c.company_name, 'Individual') AS company,
                COALESCE(NULLIF(CONCAT_WS(' ', req_user.first_name, req_user.last_name), ''), req_user.email, 'Customer') AS customer,
                COUNT(t.ticket_id)::int AS tickets,
                COUNT(t.ticket_id) FILTER (WHERE t.status_id NOT IN (3, 4))::int AS active_tickets,
                COALESCE(MODE() WITHIN GROUP (ORDER BY NULLIF(t.concern_type, '')), 'Other') AS frequent_issue
            {_ticket_base()}
            {where}
            GROUP BY req_user.user_id, c.company_name, req_user.first_name, req_user.last_name, req_user.email
            ORDER BY tickets DESC
            LIMIT 50
        """, params)
        trends = _fetchall(cursor, f"""
            SELECT TO_CHAR(DATE_TRUNC('month', t.date_created), 'Mon YYYY') AS label, COUNT(*)::int AS count
            {_ticket_base()}
            {where}
            GROUP BY DATE_TRUNC('month', t.date_created)
            ORDER BY DATE_TRUNC('month', t.date_created)
        """, params)
        table = [dict(row) for row in rows]
        return jsonify({
            "status": "success",
            "summary": {
                "customers": len(table),
                "ticket_volume": sum(int(r.get("tickets") or 0) for r in table),
                "active_customers": sum(1 for r in table if int(r.get("active_tickets") or 0) > 0),
                "inactive_customers": sum(1 for r in table if int(r.get("active_tickets") or 0) == 0),
            },
            "charts": {
                "company_distribution": [{"label": r["company"], "value": int(r["tickets"] or 0)} for r in table[:10]],
                "trends": _count_map(trends),
            },
            "table": table,
        }), 200
    except Exception as e:
        print(f"Customer analytics error: {e}")
        return _json_error("Failed to fetch customer analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/sla", methods=["GET"])
@role_required("admin")
def sla_analytics():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        service_table = _sla_service_rows(cursor)
        product_category_table = _sla_product_category_rows(cursor)
        return jsonify({
            "status": "success",
            "summary": {
                "resolved": sum(int(r.get("resolved") or 0) for r in product_category_table),
                "within_sla": sum(int(r.get("within_sla") or 0) for r in product_category_table),
                "breaches": sum(int(r.get("breaches") or 0) for r in product_category_table),
                "sla_compliance": round((sum(int(r.get("within_sla") or 0) for r in product_category_table) / max(1, sum(int(r.get("resolved") or 0) for r in product_category_table))) * 100, 1),
            },
            "charts": {
                "service_sla": [{"label": r["service_type"], "value": r["sla_compliance"]} for r in service_table],
                "product_category_sla": [{"label": r["product_category"], "value": r["sla_compliance"]} for r in product_category_table],
                "resolution_efficiency": [{"label": r["product_category"], "value": float(r.get("avg_resolution_hours") or 0)} for r in product_category_table],
                "trend": [{"label": r["product_category"], "value": r["sla_compliance"]} for r in product_category_table],
                "efficiency": [{"label": r["product_category"], "value": float(r.get("avg_resolution_hours") or 0)} for r in product_category_table],
            },
            "table": product_category_table,
            "service_table": service_table,
        }), 200
    except Exception as e:
        print(f"SLA analytics error: {e}")
        return _json_error("Failed to fetch SLA analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/system-usage", methods=["GET"])
@role_required("admin")
def system_usage_analytics():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        where, params = _login_filters("lh")
        summary = _fetchone(cursor, f"""
            SELECT
                COUNT(DISTINCT lh.user_id)::int AS daily_active_users,
                COUNT(*)::int AS login_frequency,
                COUNT(*) FILTER (WHERE LOWER(COALESCE(lh.status, '')) = 'failed')::int AS failed_logins
            FROM login_history lh
            LEFT JOIN "system_user" su ON su.user_id = lh.user_id
            {where}
        """, params, {})
        timeline = _fetchall(cursor, f"""
            SELECT TO_CHAR(DATE_TRUNC('day', lh.login_time), 'YYYY-MM-DD') AS label, COUNT(*)::int AS count
            FROM login_history lh
            LEFT JOIN "system_user" su ON su.user_id = lh.user_id
            {where}
            GROUP BY DATE_TRUNC('day', lh.login_time)
            ORDER BY DATE_TRUNC('day', lh.login_time)
        """, params)
        devices = _fetchall(cursor, f"""
            SELECT COALESCE(NULLIF(lh.device, ''), 'Unknown') AS label, COUNT(*)::int AS count
            FROM login_history lh
            LEFT JOIN "system_user" su ON su.user_id = lh.user_id
            {where}
            GROUP BY COALESCE(NULLIF(lh.device, ''), 'Unknown')
            ORDER BY count DESC
            LIMIT 8
        """, params)
        roles = _fetchall(cursor, f"""
            SELECT COALESCE(su.user_type, 'guest') AS label, COUNT(*)::int AS count
            FROM login_history lh
            LEFT JOIN "system_user" su ON su.user_id = lh.user_id
            {where}
            GROUP BY COALESCE(su.user_type, 'guest')
            ORDER BY count DESC
        """, params)
        hours = _fetchall(cursor, f"""
            SELECT TO_CHAR(DATE_TRUNC('hour', lh.login_time), 'HH24:00') AS label, COUNT(*)::int AS count
            FROM login_history lh
            LEFT JOIN "system_user" su ON su.user_id = lh.user_id
            {where}
            GROUP BY DATE_TRUNC('hour', lh.login_time)
            ORDER BY DATE_TRUNC('hour', lh.login_time)
        """, params)
        return jsonify({
            "status": "success",
            "summary": summary,
            "charts": {
                "timeline": _count_map(timeline),
                "devices": _count_map(devices),
                "roles": _count_map(roles),
                "peak_hours": _count_map(hours),
            },
            "table": [dict(row) for row in timeline],
        }), 200
    except Exception as e:
        print(f"System usage analytics error: {e}")
        return _json_error("Failed to fetch system usage analytics")
    finally:
        cursor.close()
        conn.close()


@analytics_bp.route("/analytics/notifications", methods=["GET"])
@role_required("admin")
def notifications_analytics():
    conn, cursor = _connection()
    if not conn:
        return _json_error("Database connection failed")
    try:
        announcements = _fetchall(cursor, """
            SELECT
                a.announcement_id,
                a.title,
                a.priority,
                a.created_at,
                COUNT(r.user_id)::int AS reads
            FROM announcements a
            LEFT JOIN announcement_reads r ON r.announcement_id = a.announcement_id
            GROUP BY a.announcement_id, a.title, a.priority, a.created_at
            ORDER BY reads DESC, a.created_at DESC
            LIMIT 25
        """, fallback=[])
        notification_total = _fetchone(
            cursor,
            "SELECT COUNT(*)::int AS total FROM notifications",
            fallback={"total": 0},
        ).get("total") or 0
        total_users = _fetchone(cursor, 'SELECT COUNT(*)::int AS total FROM "system_user"', fallback={"total": 0}).get("total") or 0
        sent = len(announcements) + int(notification_total)
        total_reads = sum(int(row.get("reads") or 0) for row in announcements)
        reach_possible = max(1, sent * int(total_users or 0))
        table = [dict(row) for row in announcements]
        return jsonify({
            "status": "success",
            "summary": {
                "notifications_sent": sent,
                "announcement_reach": total_reads,
                "engagement_rate": round((total_reads / reach_possible) * 100, 1) if sent else 0,
                "unread_estimate": max(0, reach_possible - total_reads) if sent else 0,
            },
            "charts": {
                "engagement": [{"label": row.get("title") or "Announcement", "value": int(row.get("reads") or 0)} for row in table[:10]],
                "read_unread": [
                    {"label": "Read", "value": total_reads},
                    {"label": "Unread", "value": max(0, reach_possible - total_reads) if sent else 0},
                ],
            },
            "table": table,
        }), 200
    except Exception as e:
        print(f"Notifications analytics error: {e}")
        return _json_error("Failed to fetch notification analytics")
    finally:
        cursor.close()
        conn.close()


def _rows_for_report(category):
    conn, cursor = _connection()
    if not conn:
        return []
    try:
        if category == "tickets":
            return [dict(row) for row in _ticket_dataset(cursor, limit=1000)]
        if category == "ticket-categories":
            charts = _ticket_charts(cursor)
            rows = []
            for report_type, chart_key in (
                ("Product Category", "product_categories"),
                ("Product Brand", "product_brands"),
                ("Concern Type", "concern_types"),
            ):
                for item in charts.get(chart_key, []):
                    rows.append({
                        "type": report_type,
                        "name": item.get("label") or "Unspecified",
                        "count": item.get("value") or 0,
                    })
            return rows
        if category == "technicians":
            where, params = _filters("t", role_column="su.user_type")
            rows = [dict(row) for row in _fetchall(cursor, f"""
                SELECT
                    COALESCE(NULLIF(CONCAT_WS(' ', su.first_name, su.last_name), ''), su.email, 'Technician') AS technician,
                    COUNT(t.ticket_id)::int AS tickets_assigned,
                    COUNT(t.ticket_id) FILTER (WHERE t.status_id IN (3, 4))::int AS tickets_resolved,
                    COUNT(t.ticket_id) FILTER (WHERE t.status_id NOT IN (3, 4))::int AS pending_tickets,
                    ROUND(AVG(EXTRACT(EPOCH FROM (t.last_updated - t.date_created)) / 3600.0)
                        FILTER (WHERE t.status_id IN (3, 4)), 2) AS avg_resolution_hours,
                    COUNT(t.ticket_id) FILTER (
                        WHERE t.status_id IN (3, 4)
                          AND t.last_updated <= t.date_created + INTERVAL '72 hours'
                    )::int AS within_sla,
                    COALESCE(MODE() WITHIN GROUP (ORDER BY NULLIF(t.concern_type, '')), 'Other') AS common_concern
                FROM technician tech
                JOIN "system_user" su ON su.user_id = tech.user_id
                LEFT JOIN ticket t ON t.technician_id = tech.technician_id
                {where}
                GROUP BY tech.technician_id, su.first_name, su.last_name, su.email
                ORDER BY tickets_resolved DESC
            """, params)]
            for row in rows:
                assigned = int(row.get("tickets_assigned") or 0)
                resolved = int(row.get("tickets_resolved") or 0)
                within_sla = int(row.get("within_sla") or 0)
                row["sla_compliance"] = round((within_sla / resolved) * 100, 1) if resolved else 0
                row["performance_score"] = round((resolved * 0.55) + (row["sla_compliance"] * 0.35) + max(0, 10 - assigned) * 0.1, 1)
                row["workload_distribution"] = assigned
            return rows
        if category == "customers":
            where, params = _filters("t", role_column="req_user.user_type")
            return [dict(row) for row in _fetchall(cursor, f"""
                SELECT
                    COALESCE(c.company_name, 'Individual') AS company,
                    COALESCE(NULLIF(CONCAT_WS(' ', req_user.first_name, req_user.last_name), ''), req_user.email, 'Customer') AS customer,
                    COUNT(t.ticket_id)::int AS tickets,
                    COUNT(t.ticket_id) FILTER (WHERE t.status_id NOT IN (3, 4))::int AS active_tickets,
                    COALESCE(MODE() WITHIN GROUP (ORDER BY NULLIF(t.concern_type, '')), 'Other') AS frequent_issue
                {_ticket_base()}
                {where}
                GROUP BY req_user.user_id, c.company_name, req_user.first_name, req_user.last_name, req_user.email
                ORDER BY tickets DESC
            """, params)]
        if category == "sla":
            return [
                {
                    "product_category": row.get("product_category") or "Uncategorized",
                    "resolved_tickets": row.get("resolved") or 0,
                    "within_sla": row.get("within_sla") or 0,
                    "sla_breaches": row.get("breaches") or 0,
                    "sla_compliance": row.get("sla_compliance") or 0,
                    "average_resolution_hours": row.get("avg_resolution_hours") or 0,
                }
                for row in _sla_product_category_rows(cursor)
            ]
        if category == "quickfix-feedback":
            return _quickfix_report_rows(cursor)
        return []
    finally:
        cursor.close()
        conn.close()


def _csv_response(rows, filename):
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}.csv"})


def _xlsx_response(rows, filename):
    headers = list(rows[0].keys()) if rows else ["message"]
    if not rows:
        rows = [{"message": "No data available"}]
    sheet_rows = []
    sheet_rows.append("<row>" + "".join(f"<c t=\"inlineStr\"><is><t>{escape(str(h))}</t></is></c>" for h in headers) + "</row>")
    for row in rows:
        sheet_rows.append("<row>" + "".join(f"<c t=\"inlineStr\"><is><t>{escape(str(row.get(h, '')))}</t></is></c>" for h in headers) + "</row>")
    sheet = f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    mem.seek(0)
    return Response(mem.read(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"})


def _pdf_response(rows, filename):
    def clean(value):
        text = "" if value is None else str(value)
        return " ".join(text.replace("\r", " ").replace("\n", " ").split())

    def pdf_escape(value):
        return clean(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def wrap_text(text, width=92):
        words = clean(text).split()
        if not words:
            return [""]
        lines = []
        line = words[0]
        for word in words[1:]:
            if len(line) + len(word) + 1 <= width:
                line = f"{line} {word}"
            else:
                lines.append(line)
                line = word
        lines.append(line)
        return lines

    display_rows = rows[:80]
    headers = list(display_rows[0].keys())[:6] if display_rows else ["message"]
    title = f"AlliTrack {filename} Report"
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    pages = []
    current = [
        ("title", title),
        ("meta", f"Generated: {generated}"),
        ("meta", f"Rows included: {len(display_rows)}"),
        ("space", ""),
    ]

    def push_line(style, text=""):
        nonlocal current
        if len(current) >= 48:
            pages.append(current)
            current = [("title", title), ("meta", f"Continued - generated {generated}"), ("space", "")]
        current.append((style, text))

    if not display_rows:
        push_line("body", "No data matched the selected filters.")
    else:
        push_line("header", " | ".join(h.replace("_", " ").title() for h in headers))
        push_line("rule", "-" * 96)
        for index, row in enumerate(display_rows, start=1):
            compact = " | ".join(clean(row.get(header, "")) for header in headers)
            for line_index, line in enumerate(wrap_text(f"{index}. {compact}", 104)):
                push_line("body", line if line_index == 0 else f"   {line}")
            push_line("space", "")

    if current:
        pages.append(current)

    objects = []
    page_ids = []
    font_id = 3

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("")  # Filled after page ids are known.
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page in pages:
        commands = ["BT"]
        y = 760
        for style, text in page:
            if style == "title":
                commands.append(f"/F1 16 Tf 1 0 0 1 48 {y} Tm ({pdf_escape(text)}) Tj")
                y -= 24
            elif style == "header":
                commands.append(f"/F1 10 Tf 1 0 0 1 48 {y} Tm ({pdf_escape(text)}) Tj")
                y -= 16
            elif style == "meta":
                commands.append(f"/F1 9 Tf 1 0 0 1 48 {y} Tm ({pdf_escape(text)}) Tj")
                y -= 14
            elif style == "rule":
                commands.append(f"/F1 8 Tf 1 0 0 1 48 {y} Tm ({pdf_escape(text)}) Tj")
                y -= 12
            elif style == "space":
                y -= 8
            else:
                commands.append(f"/F1 9 Tf 1 0 0 1 48 {y} Tm ({pdf_escape(text)}) Tj")
                y -= 13
        commands.append("ET")
        stream = "\n".join(commands)
        content_id = len(objects) + 1
        page_id = len(objects) + 2
        objects.append(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>")
        page_ids.append(page_id)

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>"

    pdf_parts = ["%PDF-1.4\n"]
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1", errors="replace")) for part in pdf_parts))
        pdf_parts.append(f"{object_id} 0 obj\n{body}\nendobj\n")
    xref_offset = sum(len(part.encode("latin-1", errors="replace")) for part in pdf_parts)
    pdf_parts.append(f"xref\n0 {len(objects) + 1}\n")
    pdf_parts.append("0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_parts.append(f"{offset:010d} 00000 n \n")
    pdf_parts.append(f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF")
    pdf = "".join(pdf_parts).encode("latin-1", errors="replace")
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}.pdf"})


@analytics_bp.route("/reports/<category>/export", methods=["GET"])
@role_required("admin")
def export_report(category):
    if category not in {"tickets", "ticket-categories", "technicians", "customers", "sla", "quickfix-feedback"}:
        return _json_error("Unsupported report category", 404)
    fmt = (request.args.get("format") or "csv").lower()
    rows = _rows_for_report(category)
    filename = f"AlliTrack_{category}_{datetime.utcnow().strftime('%Y%m%d')}"

    # 🌟 LOG THE DATA EXPORT
    from flask import g
    from Backend.routes.utils import log_system_event
    from Backend.routes.rbac import get_current_user
    current_user = getattr(g, "current_user", None) or get_current_user()
    admin_id = current_user.get("user_id") if current_user else "System"

    log_system_event(
        user_identifier=str(admin_id),
        category="Analytics & Reports",
        action="Data Exported",
        log_level="WARNING",
        description=f"Administrator exported the {category.replace('-', ' ').title()} report as {fmt.upper()}."
    )

    if fmt == "xlsx":
        return _xlsx_response(rows, filename)
    if fmt == "pdf":
        return _pdf_response(rows, filename)
    return _csv_response(rows, filename)
