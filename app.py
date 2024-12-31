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
        # Save Customer Data
        customer_data = {
            "first_name": order_data['data']['customer']['first_name'],
            "last_name": order_data['data']['customer'].get('last_name', ''),
            "email": order_data['data']['customer'].get('email', ''),
            "phone": f"{order_data['data']['customer']['mobile_code']}{order_data['data']['customer']['mobile']}",
            "city": order_data['data']['shipping']['address']['city'],
            "country": order_data['data']['shipping']['address']['country']
        }
        customer_response = supabase.table("customers").insert(customer_data).execute()
        customer_id = customer_response.data[0]['id']

        # Save Order Data
        order_data_payload = {
            "merchant_id": order_data['data']['merchant_id'],
            "order_reference": order_data['data']['reference_id'],
            "status": order_data['data']['status']['name'],
            "total_amount": order_data['data']['amounts']['total']['amount'],
            "currency": order_data['data']['amounts']['total']['currency']
        }
        order_response = supabase.table("orders").insert(order_data_payload).execute()
        order_id = order_response.data[0]['id']

        # Save Order Details
        order_details_payload = {
            "order_id": order_id,
            "customer_id": customer_id,
            "payment_method": format_payment_method(order_data['data']['payment_method']),
            "receipt_image_url": order_data['data'].get('receipt_image_url', ''),
            "amount_subtotal": order_data['data']['amounts'].get('subtotal', {}).get('amount', 0),
            "amount_shipping": order_data['data']['amounts'].get('shipping', {}).get('amount', 0),
            "amount_tax": order_data['data']['amounts'].get('tax', {}).get('amount', 0),
            "amount_discount": order_data['data']['amounts'].get('discount', {}).get('amount', 0),
            "amount_total": order_data['data']['amounts']['total']['amount']
        }
        supabase.table("order_details").insert(order_details_payload).execute()

        # Save Order Items
        for item in order_data['data']['items']:
            order_item_payload = {
                "order_id": order_id,
                "product_name": item['name'],
                "sku": item.get('sku', ''),
                "quantity": item['quantity'],
                "unit_price": item['price']['amount'],
                "discount": item.get('discount', {}).get('amount', 0),
                "weight": item.get('weight', 0),
                "currency": item['price']['currency']
            }
            supabase.table("order_items").insert(order_item_payload).execute()

        # Save Order Shipment
        shipment_data = order_data['data'].get('shipment', {})
        if shipment_data:
            shipment_payload = {
                "order_id": order_id,
                "courier_name": shipment_data.get('courier', ''),
                "tracking_number": shipment_data.get('tracking_number', ''),
                "shipment_status": shipment_data.get('status', ''),
                "pickup_street_name": shipment_data.get('pickup', {}).get('street', ''),
                "pickup_city": shipment_data.get('pickup', {}).get('city', ''),
                "pickup_postal_code": shipment_data.get('pickup', {}).get('postal_code', ''),
                "pickup_country": shipment_data.get('pickup', {}).get('country', ''),
                "delivery_street_name": shipment_data.get('delivery', {}).get('street', ''),
                "delivery_city": shipment_data.get('delivery', {}).get('city', ''),
                "delivery_postal_code": shipment_data.get('delivery', {}).get('postal_code', ''),
                "delivery_country": shipment_data.get('delivery', {}).get('country', ''),
                "shipping_cost": shipment_data.get('cost', {}).get('amount', 0),
                "is_international": shipment_data.get('is_international', False)
            }
            supabase.table("order_shipments").insert(shipment_payload).execute()

        app.logger.debug("Order saved successfully to Supabase")
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

# Webhook Route
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    try:
        data = request.get_json(force=True)
        app.logger.debug("Received webhook: %s", data)

        event_handlers = {
            'order.created': process_order_created,
            'order.updated': process_order_updated
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
