from flask import Flask, request, jsonify
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

API_URL = "https://messages.analyticalab.net/api/send"
INSTANCE_ID = "67690EC01B604"
ACCESS_TOKEN = "676897d9b52e5"
AUTH_KEY = "ory_at_Im2hv5VzGhumvXxg7Q-eEjKIawo7bp97f0rv88nd6EE.1qnxMtHdPYTmXS66iJbECc8qmqm03N78GgbqO4F0MWk"

def send_text_message(phone, message):
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
    response = requests.post(API_URL, headers=headers, json=payload)
    app.logger.debug("WhatsApp API Response: %s", response.json())
    return response.json()

def format_order_details(items):
    order_details = ""
    for item in items:
        name = item.get('name', 'غير محدد')
        quantity = item.get('quantity', 1)
        price = item.get('total_price', {}).get('amount', 0)
        subtotal = quantity * price

        order_details += (f"🛒 المنتج: {name}\n"
                          f"🔢 الكمية: {quantity}\n"
                          f"💰 السعر: {price} ريال لكل واحد\n"
                          f"🔖 الإجمالي: {subtotal} ريال\n\n")
    return order_details

def process_order(order_data):
    customer_name = order_data['data']['customer']['full_name']
    phone = order_data['data']['customer']['mobile']
    country_code = order_data['data']['customer']['mobile_code']
    checkout_url = order_data['data']['urls']['customer']
    admin_url = order_data['data']['urls']['admin']
    amount = order_data['data']['amounts']['total']['amount']
    currency = order_data['data']['amounts']['total'].get('currency', 'SAR')
    status = order_data['data']['status']['name']
    items = order_data['data'].get('items', [])
    payment_method = order_data['data']['payment_method']
    receipt_image = order_data['data']['receipt_image']
    order_source = order_data['data']['source']
    date = order_data['data']['date']['date']

    order_details = format_order_details(items)

    if "paid" in status.lower() or "مدفوع" in status:
        payment_message = "✅ تم الدفع بنجاح. لا توجد دفعات إضافية مطلوبة."
    else:
        payment_message = (f"💳 رابط الدفع: {checkout_url}\n"
                           f"يرجى إكمال الدفع في أقرب وقت ممكن لتجنب إلغاء الطلب.")

    message = (f"🔔 إشعار الطلب\n"
               f"--------------------------------------\n"
               f"👤 العميل: {customer_name}\n"
               f"📞 الهاتف: {country_code}{phone}\n"
               f"🗓️ تاريخ الطلب: {date}\n"
               f"📦 حالة الطلب: {status}\n"
               f"💵 المبلغ الإجمالي: {amount} {currency}\n"
               f"💳 طريقة الدفع: {payment_method}\n"
               f"🧾 صورة الإيصال: {receipt_image}\n"
               f"--------------------------------------\n\n"
               f"📋 تفاصيل الطلب:\n"
               f"{order_details}"
               f"--------------------------------------\n"
               f"{payment_message}\n\n"
               f"🔗 رابط الطلب (الإدارة): {admin_url}\n"
               f"📞 لخدمة العملاء، لا تتردد في الاتصال بنا.\n"
               f"شكرًا لتعاملك معنا!")

    full_phone = f"{country_code}{phone}"
    return send_text_message(full_phone, message)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        data = request.get_json(force=True)
        app.logger.debug("Received payload: %s", data)

        if data and data['event'] == 'order.created':
            response = process_order(data)
            return jsonify({"status": "Message sent", "response": response})

        return jsonify({"status": "ignored"})

    except Exception as e:
        app.logger.error("Error: %s", str(e))
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
