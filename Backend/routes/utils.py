import os
import threading
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from Backend.database import get_connection
from Backend.extensions import db
from sqlalchemy import text
from flask import request

from dotenv import load_dotenv
# Go up 2 levels (utils.py -> routes -> Backend Folder)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
load_dotenv(os.path.join(BASE_DIR, ".env"))

def send_allitrack_alert(user_id, title, message, n_type, ticket_id, status_label="Awaiting Review"):
    """
    Unified alert system: Logs an in-app notification and dispatches 
    transactional emails via Brevo USING BACKGROUND THREADS to eliminate UI lag.
    """
    
    # 🌟 NEW: We wrap your exact logic inside a nested function
    def _background_task():
        # 🔍 SAFE CONSOLE DEBUGGER
        api_key = os.environ.get('BREVO_API_KEY')
        if api_key:
            pass # Suppressed the print statement to keep your terminal clean

        conn = get_connection()
        if not conn:
            print("Utils Error: Database connection failed")
            return

        cursor = conn.cursor()
        try:
            # 1. Look up user details AND their role dynamically
            cursor.execute(
                'SELECT email, first_name, last_name, user_type FROM "system_user" WHERE user_id = %s',
                (user_id,)
            )
            user_row = cursor.fetchone()
            if not user_row:
                print(f"Utils Error: User ID {user_id} not found. Aborting alert.")
                return

            user_email = user_row[0] if isinstance(user_row, tuple) else user_row.get("email")
            f_name = user_row[1] if isinstance(user_row, tuple) else user_row.get("first_name") or ""
            l_name = user_row[2] if isinstance(user_row, tuple) else user_row.get("last_name") or ""
            user_full_name = f"{f_name} {l_name}".strip() or "AlliTrack User"
            
            # Extract role to conditionally format the email
            user_role = str(user_row[3] if isinstance(user_row, tuple) else (user_row.get("user_type") or "client")).lower()

            # 2. Save Notification to the PostgreSQL Dashboard Table
            cursor.execute(
                """
                INSERT INTO notifications (user_id, title, message, type, ticket_id, unread, created_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                """,
                (user_id, title, message, n_type, ticket_id)
            )
            conn.commit()
            print(f"In-app notification logged successfully for Ticket #{ticket_id}")

        except Exception as db_err:
            print(f"Database Notification Logging Failure: {db_err}")
            conn.rollback()
            return
        finally:
            cursor.close()
            conn.close()

        # 3. Process Labels for the Brevo Email Header Configuration
        display_title = title
        if "Ticket Status Updated" in title:
            display_title = "Ticket Status Updated"
        elif "Ticket Submission Confirmed" in title:
            display_title = "Ticket Submission Confirmed"

        # 🌟 DYNAMIC EMAIL ROUTING
        client_processing_footer = ""
        dashboard_link = "https://group6-bizally.onrender.com/user/notifications.html"

        if user_role == 'client':
            client_processing_footer = "<p>Our technical team is processing this file. You will receive an automated update once there is a change in your ticket status.</p>"
        elif user_role == 'admin':
            dashboard_link = "https://group6-bizally.onrender.com/admin/dashboard" 
        elif user_role == 'technician':
            dashboard_link = "https://group6-bizally.onrender.com/technician/all-tickets.html" 

        # 4. Trigger Brevo Email Dispatch Engine
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
            print(f"Brevo email alert successfully sent to {user_email}")
        except ApiException as e:
            print(f"Brevo delivery engine failed to send message: {e}")

    # 🌟 NEW: Spin up a thread to run the function in the background
    thread = threading.Thread(target=_background_task)
    thread.start()

def log_system_event(user_identifier, action, log_level="INFO", description=None, status="Completed"):
    try:
        ip_address = None
        browser = "Unknown"
        device = "Unknown"
        location = "Localhost" # 🌟 Set a default so it never says "-"

        if request:
            ip_address = request.remote_addr
            raw_ua = request.headers.get('User-Agent', '')

            # Mini-Parser: Browser
            if "Edg" in raw_ua: browser = "Microsoft Edge"
            elif "Chrome" in raw_ua: browser = "Google Chrome"
            elif "Firefox" in raw_ua: browser = "Mozilla Firefox"
            elif "Safari" in raw_ua and "Chrome" not in raw_ua: browser = "Apple Safari"
            else: browser = request.user_agent.browser or "Unknown"

            # Mini-Parser: Device
            if "Windows" in raw_ua: device = "Windows PC"
            elif "Macintosh" in raw_ua or "Mac OS" in raw_ua: device = "Mac Desktop"
            elif "Linux" in raw_ua: device = "Linux PC"
            elif "Android" in raw_ua: device = "Android Mobile"
            elif "iPhone" in raw_ua or "iPad" in raw_ua: device = "iOS Mobile"
            else: device = request.user_agent.platform or "Unknown"

            # Mini-Parser: Location
            country = request.headers.get('CF-IPCountry') or request.headers.get('X-Vercel-IP-Country')
            city = request.headers.get('X-Vercel-IP-City')

            if city and country: location = f"{city}, {country}"
            elif country: location = country

        # 🌟 FIXED: Added "location" to the columns and values!
        query = text("""
            INSERT INTO system_logs 
            (log_level, user_identifier, action, description, status, ip_address, browser, device, location) 
            VALUES 
            (:log_level, :user_identifier, :action, :description, :status, :ip_address, :browser, :device, :location)
        """)

        db.session.execute(query, {
            "log_level": log_level,
            "user_identifier": str(user_identifier),
            "action": action,
            "description": description,
            "status": status,
            "ip_address": ip_address,
            "browser": browser,
            "device": device,
            "location": location  # 🌟 Passed the variable here!
        })
        db.session.commit()
        
    except Exception as e:
        print(f"⚠️ Failed to write system log: {e}")