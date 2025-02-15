"""channel.py - a simple message channel."""

from flask import Flask, request, render_template, jsonify
import json
import requests
import datetime


# Class-based application configuration
class ConfigClass(object):
    """Flask application configuration class."""

    # Flask settings
    SECRET_KEY = "This is an INSECURE secret!! DO NOT use this in production!!"


# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + ".ConfigClass")  # Configuration
app.app_context().push()  # Create an app context before initializing the app

HUB_URL = "http://localhost:5555"
HUB_AUTHKEY = "1234567890"
CHANNEL_AUTHKEY = "0987654321"
CHANNEL_NAME = "The One and Only Channel"
CHANNEL_ENDPOINT = (
    "http://localhost:5001"  # Don't forget to adjust in the bottom of the file
)
CHANNEL_FILE = "messages.json"
CHANNEL_TYPE_OF_SERVICE = "aiweb24:chat"


@app.cli.command("register")
def register_command():
    """Register the channel with the hub by sending a POST request.

    This function sends the channel information to the hub server to
    register it and create a new channel.

    Returns:
        None

    """
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # Send a POST request to server /channels
    response = requests.post(
        HUB_URL + "/channels",
        headers={"Authorization": "authkey " + HUB_AUTHKEY},
        data=json.dumps(
            {
                "name": CHANNEL_NAME,
                "endpoint": CHANNEL_ENDPOINT,
                "authkey": CHANNEL_AUTHKEY,
                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
            }
        ),
    )

    if response.status_code != 200:
        print("Error creating channel: " + str(response.status_code))
        print(response.text)
        return


def check_authorization(request):
    """Check if the authorization header is valid.

    Args:
        request (flask.Request): The incoming request to check.

    Returns:
        bool: True if authorization is valid, False otherwise.

    """
    global CHANNEL_AUTHKEY
    # Check if Authorization header is present
    if "Authorization" not in request.headers:
        return False
    # Check if the authorization header is valid
    if request.headers["Authorization"] != "authkey " + CHANNEL_AUTHKEY:
        return False
    return True


@app.route("/health", methods=["GET"])
def health_check():
    """Check the health status of the channel.

    Returns:
        JSON: A JSON response containing the channel name if authorized,
               or an error message if unauthorized.

    """
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({"name": CHANNEL_NAME}), 200


# GET: Return list of messages
@app.route("/", methods=["GET"])
def home_page():
    """Return a list of messages in JSON format.

    This function handles GET requests to fetch all messages.

    Returns:
        JSON: A JSON response containing the list of messages if authorized,
               or an error message if unauthorized.

    """
    if not check_authorization(request):
        return "Invalid authorization", 400
    # Fetch channels from server
    return jsonify(read_messages())


# POST: Send a message
@app.route("/", methods=["POST"])
def send_message():
    """Receive and store a new message in the channel.

    This function handles POST requests to add a new message.

    Returns:
        str: A response indicating success ("OK") or an error message.

    """
    # Fetch channels from server
    # Check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # Check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not "content" in message:
        return "No content", 400
    if not "sender" in message:
        return "No sender", 400
    if not "timestamp" in message:
        return "No timestamp", 400
    if "extra" in message:
        extra = message["extra"]
    else:
        extra = None

    # Add message to messages
    messages = read_messages()
    messages.append(
        {
            "content": message["content"],
            "sender": message["sender"],
            "timestamp": message["timestamp"],
            "extra": extra,
        }
    )
    save_messages(messages)
    return "OK", 200


def read_messages():
    """Read messages from the messages file.

    Returns:
        list: A list of messages from the file, or an empty list if file not found.

    """
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, "r")
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages


def save_messages(messages):
    """Save a list of messages to the messages file.

    Args:
        messages (list): The list of messages to save.

    Returns:
        None

    """
    global CHANNEL_FILE
    with open(CHANNEL_FILE, "w") as f:
        json.dump(messages, f)

def init_message():
    inital_message = {
            "content": "Hello to our server. Here we discuss...",
            "sender": "Server",
            "timestamp": datetime.datetime.now().isoformat()
        }
    save_messages([inital_message])


# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == "__main__":
    init_message()
    app.run(port=5001, debug=True)
