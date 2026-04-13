from flask import Flask, request, render_template_string
from redis import Redis
import socket
import requests

app = Flask(__name__)
db = Redis(host="shop_db", port=6379, decode_responses=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Microservice Shop</title>
    <style>
        body { font-family: sans-serif; padding: 40px; background: #f4f7f6; }
        .container { background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: auto; }
        h1 { color: #333; }
        .info { font-size: 0.9em; color: #666; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .balance-box { background: #e7f3ff; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-weight: bold; color: #0056b3; }
        select, button { padding: 10px; font-size: 16px; margin-top: 10px; }
        button { background-color: #28a745; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #218838; }
        ul { background: #eee; padding: 20px; border-radius: 5px; list-style-type: none; }
        li { border-bottom: 1px solid #ddd; padding: 5px 0; }
        .link { margin-top: 20px; display: block; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Checkout Service</h1>
        <div class="info">
            Service Instance: <b>{{ container_id }}</b><br/>
            Database: <b>shop_db (Shared Redis)</b>
        </div>

        <div class="balance-box">
            Your Current Balance: ${{ balance }}
        </div>

        <form method="POST" action="/order/submit">
            <h3>Select a Product:</h3>
            <select name="sku" style="width: 100%;">
                <option value="sku:001">iPhone 15 Pro — $999</option>
                <option value="sku:002">MacBook Air — $1200</option>
                <option value="sku:003">Sony PS5 — $500</option>
            </select>
            <br/><br/>
            <button type="submit" style="width: 100%;">Buy Now (Place Order)</button>
        </form>

        <h3>Order History</h3>
        <ul>
            {% for log in logs %}
                <li>{{ log }}</li>
            {% else %}
                <li>No orders yet.</li>
            {% endfor %}
        </ul>
        <a class="link" href="/product/" target="_blank">View Inventory</a>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    logs = db.lrange("order_history", 0, 4)
    container_id = socket.gethostname()
    
    # Fetch current balance from Money Service
    try:
        balance_resp = requests.get("http://money-app:5000/balance")
        balance = balance_resp.json().get("balance", "0")
    except Exception:
        balance = "Error"

    return render_template_string(HTML_TEMPLATE, logs=logs, container_id=container_id, balance=balance)

@app.route("/submit", methods=["POST"])
def submit_order():
    sku = request.form["sku"]
    try:
        # Call Product Service to reduce stock and get price
        prod_resp = requests.post("http://product-app:5000/reduce_stock", json={"sku": sku})
        prod_data = prod_resp.json()

        if prod_resp.status_code == 200 and prod_data["success"]:
            price = int(prod_data.get("price", 0))

            # Call Money Service to deduct funds
            money_resp = requests.post("http://money-app:5000/deduct", json={"amount": price})
            money_data = money_resp.json()

            if money_resp.status_code == 200:
                order_id = db.incr("order_id_counter")
                log_message = f"Order #{order_id}: {prod_data['product_name']} - Paid ${price}"
                db.lpush("order_history", log_message)
                
                # Show updated balance on the success page
                return f"""
                    <div style="font-family:sans-serif; padding:40px; text-align:center;">
                        <h2>Order Successful!</h2>
                        <p>{log_message}</p>
                        <h3 style="color:#28a745;">Updated Balance: ${money_data['new_balance']}</h3>
                        <a href='/order/'>Back to Shop</a>
                    </div>
                """
            else:
                return f"<h2>Payment Failed</h2><p>{money_data.get('message')}</p><a href='/order/'>Back</a>"
        else:
            return f"<h2>Order Failed</h2><p>{prod_data.get('message')}</p><a href='/order/'>Back</a>"

    except Exception as e:
        return f"<h2>System Error</h2><p>{str(e)}</p><a href='/order/'>Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
