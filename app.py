from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# WhatsApp API Config
INSTANCE_ID = "67690EC01B604"
ACCESS_TOKEN = "676897d9b52e5"
AUTH_KEY = "ory_at_Im2hv5VzGhumvXxg7Q-eEjKIawo7bp97f0rv88nd6EE.1qnxMtHdPYTmXS66iJbECc8qmqm03N78GgbqO4F0MWk"

# Webhook Route
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        data = request.json

        # Check the event type
        if data['event'] == 'order.created':
            customer = data['data']['customer']
            amounts = data['data']['amounts']
            urls = data['data']['urls']
            status = data['data']['status']['name']

            # Prepare the WhatsApp message content
            message = (
                f"مرحبا {customer['full_name']}!\n\n"
                f"تم استلام طلبك بنجاح.\n"
                f"المبلغ الإجمالي: {amounts['total']['amount']} ريال\n"
                f"حالة الطلب: {status}\n"
                f"رابط الدفع والمتابعة: {urls['customer']}\n\n"
                f"شكرًا لتعاملك معنا!"
            )

            # Full phone number
            full_phone = f"{customer['mobile_code']}{customer['mobile']}"

            # Payload for WhatsApp API
            payload = {
                "number": full_phone,
                "type": "text",
                "message": message,
                "instance_id": INSTANCE_ID,
                "access_token": ACCESS_TOKEN
            }

            # Headers for the request
            headers = {
                "Authorization": f"Bearer {AUTH_KEY}",  # Add Authorization header
                "Content-Type": "application/json"
            }

            # Send the WhatsApp message
            response = requests.post(
                'https://messages.analyticalab.net/api/send',
                json=payload,
                headers=headers
            )

            # Log the response
            if response.status_code == 200:
                return jsonify({"status": "Message sent successfully", "response": response.json()})
            else:
                # Log the error if the request fails
                return jsonify({
                    "status": "Message failed",
                    "error": response.text,
                    "code": response.status_code
                }), 400

        # If the event is not 'order.created', ignore it
        return jsonify({"status": "Event ignored"})

    except Exception as e:
        # Log any unexpected errors
        return jsonify({"status": "Error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
