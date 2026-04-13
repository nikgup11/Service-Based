from flask import Flask, request, render_template_string
from redis import Redis
import socket
import requests

app = Flask(__name__)

# Shared database
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
        .info { font-size: 0.9em; color: #666; margin-bottom: 20px; }
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

        <form method="POST" action="/order/submit">
            <h3>Select a Product:</h3>
            <select name="sku" style="width: 100%;">
                <option value="sku:001">iPhone 15 Pro</option>
                <option value="sku:002">MacBook Air</option>
                <option value="sku:003">Sony PS5</option>
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

        <a class="link" href="/product/" target="_blank">View Inventory (Product Service)</a>
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    logs = db.lrange("order_history", 0, 4)
    container_id = socket.gethostname()
    return render_template_string(HTML_TEMPLATE, logs=logs, container_id=container_id)


@app.route("/submit", methods=["POST"])
def submit_order():
    sku = request.form["sku"]
    try:
        # 1. Reduce Stock and get Product Info (including price)
        prod_resp = requests.post("http://product-app:5000/reduce_stock", json={"sku": sku})
        prod_data = prod_resp.json()

        if prod_resp.status_code == 200 and prod_data["success"]:
            # 2. Get price (ensure product_service returns it in /reduce_stock)
            price = int(prod_data.get("price", 0)) 

            # 3. Deduct Money
            money_resp = requests.post("http://money-app:5000/deduct", json={"amount": price})
            money_data = money_resp.json()

            if money_resp.status_code == 200:
                order_id = db.incr("order_id_counter")
                log_message = f"Order #{order_id}: {prod_data['product_name']} - Paid ${price}"
                db.lpush("order_history", log_message)
                return f"<h2>Success!</h2><p>{log_message}</p><a href='/order/'>Back</a>"
            else:
                return f"<h2>Payment Failed</h2><p>{money_data['message']}</p>"
        
        return f"<h2>Order Failed</h2><p>{prod_data.get('message')}</p>"

    except Exception as e:
        return f"<h2>System Error</h2><p>{str(e)}</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
