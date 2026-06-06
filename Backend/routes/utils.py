import os
import threading
import requests  # 🌟 CRITICAL FIX: Needed for IP lookups
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from Backend.database import get_connection
from Backend.extensions import db
from sqlalchemy import text
from flask import request, has_request_context  # 🌟 CRITICAL FIX: Needed to prevent crashes
from dotenv import load_dotenv

# Go up 2 levels (utils.py -> routes -> Backend Folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==========================================
# 🌟 ADVANCED TRACKERS TRANSPLANTED FROM AUTH
# ==========================================
def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("X-Real-IP") or request.remote_addr or "Unknown IP"

def _device_from_user_agent(user_agent):
    ua = (user_agent or "").lower()
    browser = "Browser"
    if "edg/" in ua: browser = "Microsoft Edge"
    elif "chrome/" in ua and "chromium" not in ua: browser = "Chrome"
    elif "firefox/" in ua: browser = "Firefox"
    elif "safari/" in ua and "chrome/" not in ua: browser = "Safari"

    os_name = "Unknown Device"
    if "windows" in ua: os_name = "Windows"
    elif "mac os" in ua or "macintosh" in ua: os_name = "macOS"
    elif "android" in ua: os_name = "Android"
    elif "iphone" in ua or "ipad" in ua: os_name = "iOS"
    elif "linux" in ua: os_name = "Linux"
    return f"{browser} on {os_name}"

def _location_from_ip(ip_address):
    if not ip_address or ip_address in {"127.0.0.1", "localhost", "::1", "Unknown IP"}:
        return "Localhost"
    if ip_address.startswith(("10.", "192.168.", "172.")):
        return "Local Network"
    
    try:
        r = requests.get(f"https://ipinfo.io/{ip_address}/json", timeout=3)
        data = r.json()
        if "city" in data and "country" in data:
            parts = [p for p in [data.get("city"), data.get("region"), data.get("country")] if p]
            if parts: return ", ".join(parts)
    except Exception:
        pass
        
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city", timeout=3)
        data = response.json()
        if data.get("status") == "success":
            parts = [data.get("city"), data.get("regionName"), data.get("country")]
            location = ", ".join([part for part in parts if part])
            return location or "Unknown Location"
    except Exception:
        pass
        
    return "Unknown Location"

# ==========================================
# 🌟 EMAIL ALERT SYSTEM
# ==========================================
def send_allitrack_alert(user_id, title, message, n_type, ticket_id, status_label="Awaiting Review"):
    def _background_task():
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            return

        conn = get_connection()
        if not conn:
            return

        cursor = conn.cursor()
        try:
            cursor.execute('SELECT email, first_name, last_name, user_type FROM "system_user" WHERE user_id = %s', (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return

            user_email = user_row[0] if isinstance(user_row, tuple) else user_row.get("email")
            f_name = user_row[1] if isinstance(user_row, tuple) else user_row.get("first_name") or ""
            l_name = user_row[2] if isinstance(user_row, tuple) else user_row.get("last_name") or ""
            user_full_name = f"{f_name} {l_name}".strip() or "AlliTrack User"
            user_role = str(user_row[3] if isinstance(user_row, tuple) else (user_row.get("user_type") or "client")).lower()

            cursor.execute(
                """
                INSERT INTO notifications (user_id, title, message, type, ticket_id, unread, created_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                """,
                (user_id, title, message, n_type, ticket_id)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            return
        finally:
            cursor.close()
            conn.close()

        display_title = title
        if "Ticket Status Updated" in title:
            display_title = "Ticket Status Updated"
        elif "Ticket Submission Confirmed" in title:
            display_title = "Ticket Submission Confirmed"

        client_processing_footer = ""
        dashboard_link = "https://group6-bizally.onrender.com/user/notifications.html"

        if user_role == 'client':
            client_processing_footer = "<p>Our technical team is processing this file. You will receive an automated update once there is a change in your ticket status.</p>"
        elif user_role == 'admin':
            dashboard_link = "https://group6-bizally.onrender.com/admin/dashboard" 
        elif user_role == 'technician':
            dashboard_link = "https://group6-bizally.onrender.com/technician/all-tickets.html" 

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key 
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user_email, "name": user_full_name}],
            subject=f"{display_title} (#{ticket_id})",
            html_content=f"""
            <!DOCTYPE html>
            <html>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f9;">
                <div style="max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="background-color: #2563eb; padding: 25px; text-align: center;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 24px;">AlliTrack Support</h1>
                    </div>
                    <div style="padding: 30px; color: #334155; line-height: 1.6;">
                        <h2 style="color: #1e293b; margin-top: 0;">{display_title}</h2>
                        <p>Dear {user_full_name},</p>
                        <p>{message}</p>
                        
                        <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0; font-weight: bold;">Ticket Reference: #{ticket_id}</p>
                            <p style="margin: 3px 0 0 0; font-size: 0.9rem; color: #64748b;">Status: {status_label}</p>
                        </div>

                        {client_processing_footer}
                        
                        <a href="{dashboard_link}"
                        style="display: inline-block; padding: 12px 25px; background-color: #2563eb; color: #ffffff; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">
                        View Dashboard
                        </a>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;">
                        <p style="margin: 0;">&copy; 2026 Business Alliance Inc. | AlliTrack System</p>
                        <p style="margin: 5px 0 0 0;">This is an automated message, please do not reply directly to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            sender={"name": "AlliTrack Support", "email": "noreply.allitrack@gmail.com"}
        )

        try:
            api_instance.send_transac_email(send_smtp_email)
        except ApiException as e:
            print(f"Brevo delivery engine failed to send message: {e}")
            log_system_event(
                user_identifier=str(user_id),
                category="System",
                action="Email Delivery Failed",
                log_level="ERROR",
                description=f"Brevo failed to send '{display_title}' to {user_email}.",
                status="Failed"
            )

    thread = threading.Thread(target=_background_task)
    thread.start()

# ==========================================
# 🌟 UPGRADED SYSTEM LOGGER
# ==========================================
def log_system_event(user_identifier, action, category="System", log_level="INFO", description=None, status="Completed"):
    try:
        ip_address = "Unknown"
        browser = "Unknown"
        device = "Unknown"
        location = "Localhost"

        # Safe execution: Only pull IP data if triggered by a web request!
        if has_request_context():
            ip_address = _client_ip()
            raw_ua = request.headers.get('User-Agent', '')
            
            full_device_string = _device_from_user_agent(raw_ua)
            if " on " in full_device_string:
                browser, device = full_device_string.split(" on ", 1)
            else:
                browser = full_device_string
                device = "Unknown"

            location = _location_from_ip(ip_address)

        conn = get_connection()
        if not conn:
            return

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_logs 
            (log_level, category, user_identifier, action, description, status, ip_address, browser, device, location) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (log_level, category, str(user_identifier), action, description, status, ip_address, browser, device, location)
        )
        conn.commit()
        
    except Exception as e:
        print(f"⚠️ Failed to write system log: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()