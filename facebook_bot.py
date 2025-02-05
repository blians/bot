# proxy_forward.py

from flask import Flask, request, render_template_string, redirect, url_for
import requests,os

app = Flask(__name__)

# Define the default URLs for GET and POST forwarding
URL = "https://rnubo-103-230-107-22.a.free.pinggy.link"

# Home route to show HTML form
@app.route('/', methods=['GET'])
def home():
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Proxy Forwarder</title>
            <!-- Bootstrap CSS -->
            <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h1 class="text-center">Proxy Forwarder</h1>
                <form action="/set-url" method="POST" class="mt-4">
                    <div class="form-group">
                        <label for="code">Enter Code:</label>
                        <input type="text" class="form-control" name="code" required>
                    </div>
                    <div class="form-group">
                        <label for="url">Enter New URL:</label>
                        <input type="text" class="form-control" name="url" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Submit</button>
                </form>
            </div>

            <!-- Bootstrap JS and Popper.js -->
            <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.4/dist/umd/popper.min.js"></script>
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
        </body>
        </html>
    """)

# Route to handle form submission and URL update
@app.route('/set-url', methods=['POST'])
def set_url():
    code = request.form.get('code')
    new_url = request.form.get('url')

    # Check the code (you can replace this with your own validation logic)
    if code == os.getenv("code"):
        # Example code for validation
        # Update the forwarding URL based on the form input
        global URL
        URL = new_url
        return f"<div class='container mt-5'><h2 class='text-success'>URL updated successfully! Now forwarding to: {new_url}</h2></div>"
    else:
        return "<div class='container mt-5'><h2 class='text-danger'>Invalid code! Try again.</h2></div>"

# Proxy route for both GET and POST requests
@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    print("\n\n\n\n\n"+URL)
    if request.method == 'GET':
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            if not request.args.get("hub.verify_token") == "cat":
                return "Verification token missmatch", 403
            return request.args['hub.challenge'], 200

        return "Hello world", 200
    elif request.method == 'POST':
        # Forward POST request to the defined URL
        PAGE_ACCESS_TOKEN = 'EAAVFQ6BdqPcBO4VjetTS9iS9BqqgaO4mWqcbhtxb4DDOT1zBZAu90Jsx7vcZC1BmtVKK5RqTKcxXo03JJZCZB7nZBy3cSe0jZBVNZBf6YXCw5IODhl3KAlLKq5UX1ouN49ZCqNby9xk6CoZBEShG7SqcZA5XNePeU5w32rlUSh2FZAnK4tZAf8NLwjdSG3kKwgAuPTjtpA1VWQLx3ahavIRTujs3o2G7ASgZD'

        # This is API key for facebook messenger.

        API = "https://graph.facebook.com/v18.0/me/messages?access_token="+PAGE_ACCESS_TOKEN
        data = request.get_json()
        print(data)
        try:
            # Read messages from facebook messanger.
            message = data['entry'][0]['messaging'][0]['message']
            sender_id = data['entry'][0]['messaging'][0]['sender']['id']
            # Here we get message text and check specific text so we can send response specificaly.
            request_body = {
                "recipient": {
                    "id": sender_id
                },
                "message": {
                    "text": message
                }
            }
            response = requests.post(API, json=request_body).json()
            return response
        except:
            pass

if __name__ == '__main__':
    print(9)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
    
