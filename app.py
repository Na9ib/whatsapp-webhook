from flask import Flask, request, jsonify
from supabase import create_client, Client
import requests
import logging
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configuration
SUPABASE_URL = "https://chhiksvujaaoifrlvosm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNoaGlrc3Z1amFhb2lmcmx2b3NtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzU2NzYzMzAsImV4cCI6MjA1MTI1MjMzMH0.wk6TT5s6CMmvMA2wCThu0aLJM-X9DsVfl7kqqLOMfKY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

API_URL = "https://messages.analyticalab.net/api/send"
INSTANCE_ID = "67690EC01B604"
ACCESS_TOKEN = "676897d9b52e5"
AUTH_KEY = "ory_at_Im2hv5VzGhumvXxg7Q-eEjKIawo7bp97f0rv88nd6EE.1qnxMtHdPYTmXS66iJbECc8qmqm03N78GgbqO4F0MWk"

# Utility functions
def send_whatsapp_message(phone, message):
    payload = {
        "number": phone,
        "type": "text",
        "message": message,
        "instance_id": INSTANCE_ID,
        "access_token": ACCESS_TOKEN
    }
    headers = {
        "Authorization": f"Bearer {AUTH_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        app.logger.debug("WhatsApp API Response: %s", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.error("WhatsApp API Error: %s", str(e))
        raise

def format_payment_method(method):
    payment_methods = {
        'cod': 'الدفع عند الاستلام',
        'credit': 'البطاقة البنكية',
        'bank_transfer': 'تحويل بنكي',
        'apple_pay': 'Apple Pay',
        'stc_pay': 'STC Pay'
    }
    return payment_methods.get(method, method)

def format_address(address):
    if not address:
        return "غير محدد"
    parts = []
    if address.get('shipping_address'):
        parts.append(address['shipping_address'])
    if address.get('city'):
        parts.append(address['city'])
    if address.get('postal_code'):
        parts.append(address['postal_code'])
    return "، ".join(filter(None, parts))

def format_status(status):
    status_emojis = {
        'payment_pending': '⏳',
        'under_review': '👀',
        'in_progress': '🔄',
        'shipped': '🚚',
        'delivered': '✅',
        'cancelled': '❌',
        'completed': '✨'
    }
    status_name = status.get('name', '')
    status_slug = status.get('slug', '')
    emoji = status_emojis.get(status_slug, '📦')
    return f"{emoji} {status_name}"

def save_order_to_supabase(order_data):
    try:
        data = {
            "event_type": order_data['event'],
            "customer_phone": f"{order_data['data']['customer']['mobile_code']}{order_data['data']['customer']['mobile']}",
            "customer_name": order_data['data']['customer']['first_name'],
            "order_reference": order_data['data']['reference_id'],
            "order_status": order_data['data']['status']['name'],
            "payment_method": format_payment_method(order_data['data']['payment_method']),
            "total_amount": order_data['data']['amounts']['total']['amount'],
            "currency": order_data['data']['amounts']['total']['currency'],
            "shipping_address": format_address(order_data['data'].get('shipping', {})),
        }
        response = supabase.table("orders").insert(data).execute()
        app.logger.debug("Saved to Supabase: %s", response.data)
        return response
    except Exception as e:
        app.logger.error("Error saving to Supabase: %s", str(e))
        raise

# Event Handlers
def process_order_created(order_data):
    save_order_to_supabase(order_data)
    try:
        data = order_data['data']
        customer = data['customer']
        full_phone = f"{customer['mobile_code']}{customer['mobile']}"
        
        store = data.get('store', {})
        store_name = store.get('name', {}).get('ar') if isinstance(store.get('name'), dict) else ''
        
        message = (
            f"مرحباً {customer['first_name']}! يسعدنا اختيارك لنا ✨\n\n"
            f"📋 تفاصيل طلبك المميز:\n"
            f"رقم الطلب: {data['reference_id']}\n"
            f"حالة الطلب: {format_status(data['status'])}\n"
            f"💎 القيمة: {data['amounts']['total']['amount']} {data['amounts']['total']['currency']}\n"
            f"💳 طريقة الدفع: {format_payment_method(data['payment_method'])}\n\n"
            f"📍 عنوان التوصيل:\n"
            f"{format_address(data.get('shipping', {}))}\n\n"
            f"🔍 لمتابعة طلبك الخاص:\n"
            f"{data['urls']['customer']}\n\n"
            f"نحن سعداء بخدمتك ونتطلع لتقديم تجربة استثنائية لك ✨\n"
            f"فريق {store_name} 🌟"
        )

        if data.get('is_pending_payment'):
            message += f"\n\nملاحظة: يرجى إكمال عملية الدفع خلال {data['pending_payment_ends_at']} ساعة 🕒"

        return send_whatsapp_message(full_phone, message)

    except KeyError as e:
        app.logger.error("Missing required field: %s", str(e))
        raise
    except Exception as e:
        app.logger.error("Error processing order: %s", str(e))
        raise


def process_order_updated(order_data):
    save_order_to_supabase(order_data)
    # Existing WhatsApp message sending logic here
    try:
        data = order_data['data']
        customer = data['customer']
        full_phone = f"{customer['mobile_code']}{customer['mobile']}"
        
        store = data.get('store', {})
        store_name = store.get('name', {}).get('ar') if isinstance(store.get('name'), dict) else ''
        
        message = (
            f"مرحباً {customer['first_name']}! تم تحديث حالة طلبك ✨\n\n"
            f"📋 تفاصيل الطلب:\n"
            f"رقم الطلب: {data['reference_id']}\n"
            f"🛒 حالة الطلب: {format_status(data['status'])}\n"
            f"💎 القيمة: {data['amounts']['total']['amount']} {data['amounts']['total']['currency']}\n"
            f"💳 طريقة الدفع: {format_payment_method(data['payment_method'])}\n\n"
            f"📍 عنوان التوصيل:\n"
            f"{format_address(data.get('shipping', {}))}\n\n"
            f"🔍 تابع طلبك من هنا:\n"
            f"{data['urls']['customer']}\n\n"
            f"نحن سعداء لخدمتك، فريق {store_name} 🌟"
        )
        
        if data.get('is_pending_payment'):
            message += f"\n\nيرجى إكمال الدفع قبل {data['pending_payment_ends_at']} 🕒"
        
        if data['status']['slug'] == 'cancelled':
            message += "\n\nنأسف لإبلاغك أن طلبك قد تم إلغاؤه ❌"
        
        if data.get('shipment'):
            message += f"\n\n🚚 تتبع الشحنة: {data['shipment']['tracking_link']}"
        
        if data.get('rating_link'):
            message += f"\n\n✨ قيم تجربتك معنا: {data['rating_link']}"
        
        return send_whatsapp_message(full_phone, message)
    except KeyError as e:
        app.logger.error("Missing required field: %s", str(e))
        raise
    except Exception as e:
        app.logger.error("Error processing order update: %s", str(e))
        raise

def process_customer_login(login_data):
    try:
        data = login_data['data']
        customer = data
        full_phone = f"{customer['mobile_code']}{customer['mobile']}"
        
        message = (
            f"_(يا هلا وغلا بمن لفانا، نورت المكان وزادنا شرف بحضورك 🌟)_\n\n"
            f"```*❤️ {customer['first_name']}* مرحباً بك يا ```  \n\n"
            f"مجلسنا مجلسك ومتجرنا محلاك،  \n\n"
            f"لو احتجت أي خدمة أو استفسار، هذا رقم الواتساب تحت أمرك، وحياك الله دائماً 🌴😊"
            
        )

        return send_whatsapp_message(full_phone, message)

    except KeyError as e:
        app.logger.error("Missing required field: %s", str(e))
        raise
    except Exception as e:
        app.logger.error("Error processing login: %s", str(e))
        raise


# Webhook Route
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        data = request.get_json(force=True)
        app.logger.debug("Received webhook: %s", data)

        event_handlers = {
            'order.created': process_order_created,
            'order.updated': process_order_updated,
            'customer.login': process_customer_login
        }

        event = data.get('event')
        if event in event_handlers:
            response = event_handlers[event](data)
            return jsonify({
                "status": "success",
                "message": "Processed successfully",
                "response": response
            })

        return jsonify({
            "status": "ignored",
            "message": f"Event {event} not handled"
        })

    except Exception as e:
        app.logger.error("Webhook error: %s", str(e))
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Start the application
if __name__ == '__main__':
    app.run(debug=True)
