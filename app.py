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

def process_order(order_data):
    customer_name = order_data['data']['customer']['full_name']
    phone = order_data['data']['customer']['mobile']
    country_code = order_data['data']['customer']['mobile_code']
    checkout_url = order_data['data']['urls']['customer']
    amount = order_data['data']['amounts']['total']['amount']
    status = order_data['data']['status']['name']

    message = (f"مرحبا {customer_name}!\n\n"
               f"تم استلام طلبك بنجاح.\n"
               f"المبلغ الإجمالي: {amount} ريال\n"
               f"حالة الطلب: {status}\n"
               f"رابط الدفع والمتابعة: {checkout_url}\n\n"
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
