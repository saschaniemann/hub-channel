"""Implementation of a client of a hub-channel application."""

from flask import Flask, request, render_template, url_for, redirect
import requests
import urllib.parse
import datetime

app = Flask(__name__)

HUB_AUTHKEY = "1234567890"
HUB_URL = "http://localhost:5555"

CHANNELS = None
LAST_CHANNEL_UPDATE = None


def update_channels():
    """Fetch and update the list of channels from the server.

    This function checks if the channels have been updated within the last 60 seconds.
    If not, it makes a GET request to the server to fetch the latest channels.

    Returns:
        list: Updated channels if successful, or an error message if unsuccessful.

    """
    global CHANNELS, LAST_CHANNEL_UPDATE
    if (
        CHANNELS
        and LAST_CHANNEL_UPDATE
        and (datetime.datetime.now() - LAST_CHANNEL_UPDATE).seconds < 60
    ):
        return CHANNELS
    # fetch list of channels from server
    response = requests.get(
        HUB_URL + "/channels", headers={"Authorization": "authkey " + HUB_AUTHKEY}
    )
    if response.status_code != 200:
        return "Error fetching channels: " + str(response.text), 400
    channels_response = response.json()
    if not "channels" in channels_response:
        return "No channels in response", 400
    CHANNELS = channels_response["channels"]
    LAST_CHANNEL_UPDATE = datetime.datetime.now()
    return CHANNELS


@app.route("/")
def home_page():
    """Render the home page displaying a list of channels.

    Returns:
        HTML: Rendered home page with the list of channels.

    """
    # fetch list of channels from server
    return render_template("react_client.html")


@app.route("/show")
def show_channel():
    """Render the page to show messages from a specific channel.

    This function retrieves messages from the specified channel's endpoint.

    Returns:
        HTML: Rendered channel page with messages, or an error message if unsuccessful.

    """
    # fetch list of messages from channel
    show_channel = request.args.get("channel", None)
    if not show_channel:
        return "No channel specified", 400
    channel = None
    for c in update_channels():
        if c["endpoint"] == urllib.parse.unquote(show_channel):
            channel = c
            break
    if not channel:
        return "Channel not found", 404
    response = requests.get(
        channel["endpoint"], headers={"Authorization": "authkey " + channel["authkey"]}
    )
    if response.status_code != 200:
        return "Error fetching messages: " + str(response.text), 400
    messages = response.json()
    return render_template("channel.html", channel=channel, messages=messages)


@app.route("/post", methods=["POST"])
def post_message():
    """Send a message to a specified channel.

    This function takes the channel, message content, and sender information
    from the form data, and forwards the message to the channel's endpoint.

    Returns:
        Redirect: Redirects back to the channel page or an error message if unsuccessful.

    """
    # send message to channel
    post_channel = request.form["channel"]
    if not post_channel:
        return "No channel specified", 400
    channel = None
    for c in update_channels():
        if c["endpoint"] == urllib.parse.unquote(post_channel):
            channel = c
            break
    if not channel:
        return "Channel not found", 404
    message_content = request.form["content"]
    message_sender = request.form["sender"]
    message_timestamp = datetime.datetime.now().isoformat()
    response = requests.post(
        channel["endpoint"],
        headers={"Authorization": "authkey " + channel["authkey"]},
        json={
            "content": message_content,
            "sender": message_sender,
            "timestamp": message_timestamp,
        },
    )
    if response.status_code != 200:
        return "Error posting message: " + str(response.text), 400
    return redirect(
        url_for("show_channel") + "?channel=" + urllib.parse.quote(post_channel)
    )


# Start development web server
if __name__ == "__main__":
    app.run(port=5005, debug=True)
