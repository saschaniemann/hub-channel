"""channel.py - a simple message channel."""

from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import json
import requests
from datetime import datetime, timedelta, timezone
from better_profanity import profanity
from typing import Tuple


# Class-based application configuration
class ConfigClass(object):
    """Flask application configuration class."""

    # Flask settings
    SECRET_KEY = "This is an INSECURE secret!! DO NOT use this in production!!"


# Create Flask app
app = Flask(__name__)
CORS(app)
app.config.from_object(__name__ + ".ConfigClass")  # Configuration
app.app_context().push()  # Create an app context before initializing the app

HUB_URL = "http://vm146.rz.uni-osnabrueck.de/hub"
HUB_AUTHKEY = "Crr-K24d-2N"
CHANNEL_AUTHKEY = "0987654321"
CHANNEL_NAME = "Weather you like it or not!"
CHANNEL_ENDPOINT = "http://vm322.rz.uni-osnabrueck.de/u058/hub_channel/channel.wsgi"  # Don't forget to adjust in the bottom of the file
CHANNEL_FILE = "hub_channel/messages.json"
CHANNEL_TYPE_OF_SERVICE = "aiweb24:chat"
CHANNEL_MAX_MESSAGE_AGE = 1


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


def get_coordinates(location: str) -> Tuple[str, str]:
    """Calculate the latitude and longitude of a location using the Open Meteo API.

    Args:
        location (str): location of interest

    Raises:
        Exception: If GET request fails.

    Returns:
        Tuple[str, str]: latitude, longitude

    """
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # parameters for the API request
    params = {"name": location, "count": 1, "language": "en", "format": "json"}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        location_data = response.json().get("results", None)
        if not location_data:
            return None, None
        latitude = location_data[0].get("latitude", None)
        longitude = location_data[0].get("longitude", None)

        return latitude, longitude

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching the location data: {e}")


def get_weather(latitude: str, longitude: str) -> Tuple[str, str]:
    """Fetch weather info from open meteo API.

    Args:
        latitude (str): latitude of the point of interest
        longitude (str): longitude of the point of interest

    Raises:
        Exception: if the GET request fails or 'current_weather' is not returned by open meteo API.

    Returns:
        Tuple[str, str]: temperature[°C], windspeed[km/h]

    """
    url = "https://api.open-meteo.com/v1/forecast"

    # parameters for the API request
    params = {"latitude": latitude, "longitude": longitude, "current_weather": True}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        weather_data = response.json()
        current_weather = weather_data.get("current_weather", {})

        if current_weather:
            return current_weather["temperature"], current_weather["windspeed"]
        else:
            raise Exception("No weather info received!")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching the weather data: {e}")


def handle_commands(message, messages: list) -> None:
    """Handle commands by checking if it begins with !weather ....

    Args:
        message (str): user message
        messages (list): all messages

    """
    content = message["content"].strip()
    if content == "!weather":
        # our client didnt get the location
        if "extra" in message and message["extra"] == "ERROR":
            messages.append(
                {
                    "content": f"Sorry we were not able to get your location. Try to add your location as parameter.",
                    "sender": "Weather",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": "",
                    })
        # our client got the location
        elif "latitude" in message and "longitude" in message:
            temperature, windspeed = get_weather(message["latitude"], message["longitude"])
            messages.append(
                {
                    "content": f"Today it is going to be {temperature}°C with a windspeed of {windspeed}km/h at your place.",
                    "sender": "Weather",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": "",
                    })
        # other client used
        else:
            messages.append(
                {
                    "content": f"Sorry we were not able to get your location. Try to add your location as parameter.",
                    "sender": "Weather",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": "",
                    })
    elif content.startswith("!weather "):
        place = profanity.censor(content[9:])
        latitude, longitude = get_coordinates(place)
        if not latitude or not longitude:
            messages.append(
                {
                    "content": f"Location '{place}' not found.",
                    "sender": "Weather",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": "",
                }
            )
        else:
            temperature, windspeed = get_weather(latitude, longitude)
            messages.append(
                {
                    "content": f"Today it is going to be {temperature}°C with a windspeed of {windspeed}km/h in {place}.",
                    "sender": "Weather",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": "",
                }
            )
    elif content.startswith("!"):
        messages.append(
            {
                "content": f"Command '{profanity.censor(content)}' not found.",
                "sender": "Server",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "extra": "",
            }
        )


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
    if message["content"].strip() == "":
        return "OK", 200
    extra = None
    if "extra" in message:
        extra = message["extra"]

    # Add message to messages
    messages = read_messages()
    messages.append(
        {
            "content": profanity.censor(message["content"]),
            "sender": profanity.censor(message["sender"]),
            "timestamp": message["timestamp"],
            "extra": extra,
        }
    )

    # handle commands (starting with !)
    handle_commands(message, messages)

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
    messages = filter_old_messages(messages)
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
        messages = filter_old_messages(messages)
        json.dump(messages, f)


def filter_old_messages(messages: list) -> list:
    """Filter messages by age. Old messages get deleted.

    Args:
        messages (list): all messages

    Returns:
        list: filtered messages

    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=CHANNEL_MAX_MESSAGE_AGE)
    filtered_messages = []
    for message in messages:
        timestamp = message["timestamp"]
        iso_message_time = datetime.fromisoformat(timestamp.rstrip("Z"))
        if iso_message_time.tzinfo is None:
            iso_message_time = iso_message_time.replace(tzinfo=timezone.utc)
        if iso_message_time >= cutoff or (
            "extra" in message and message["extra"] == "INIT"
        ):
            filtered_messages.append(message)
    return filtered_messages


def init_message():
    """Save initial message."""
    inital_message = {
        "content": """Welcome to our server. Here we discuss everything that has something to do with the weather. No matter if it's in your area or anywhere in the world.
        
        If you want to know the weather in a specific location, just type !weather followed by the location. Or just leave out the location to get the weather at your place. Note: getting the weather at without providing a location only works on a https connection because otherwise your browser will not allow you to share your geolocation.""",
        "sender": "Server",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "extra": "INIT",
    }
    save_messages([inital_message])


# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == "__main__":
    init_message()
    profanity.load_censor_words()
    # app.run(port=5001, debug=True)
