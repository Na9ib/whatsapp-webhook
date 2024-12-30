from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# WhatsApp API Config
INSTANCE_ID = "67690EC01B604"
ACCESS_TOKEN = "676897d9b52e5"

# Webhook Route
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    if data['event'] == 'order.created':
        customer = data['data']['customer']
        amounts = data['data']['amounts']
        urls = data['data']['urls']
        
        # WhatsApp message content
        message = f"Hello {customer['full_name']}, your order of {amounts['total']['amount']} SAR is confirmed. " \
                  f"Track it here: {urls['customer']}"
        
        payload = {
            "number": f"{customer['mobile_code']}{customer['mobile']}",
            "type": "text",
            "message": message,
            "instance_id": INSTANCE_ID,
            "access_token": ACCESS_TOKEN
        }
        
        # Send WhatsApp Message
        response = requests.post(
            'https://messages.analyticalab.net/api/send',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        return jsonify({"status": "Message sent", "response": response.json()})
    
    return jsonify({"status": "ignored"})

if __name__ == '__main__':
    app.run(debug=True)
