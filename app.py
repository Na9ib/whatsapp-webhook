from flask import Flask, request, jsonify
import requests
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Configuration
API_URL = "https://messages.analyticalab.net/api/send"
INSTANCE_ID = "67690EC01B604"
ACCESS_TOKEN = "676897d9b52e5"
AUTH_KEY = "ory_at_Im2hv5VzGhumvXxg7Q-eEjKIawo7bp97f0rv88nd6EE.1qnxMtHdPYTmXS66iJbECc8qmqm03N78GgbqO4F0MWk"

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

def process_order_created(order_data):
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
            f"{format_address(data.get(['shipping']['address'], {}))}\n\n"
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

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        data = request.get_json(force=True)
        app.logger.debug("Received webhook: %s", data)

        event_handlers = {
            'order.created': process_order_created
            # Add other event handlers here as needed
        }

        event = data.get('event')
        if event in event_handlers:
            response = event_handlers[event](data)
            return jsonify({
                "status": "success",
                "message": "Notification sent successfully",
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

if __name__ == '__main__':
    app.run(debug=True)
