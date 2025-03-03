# Start Code for Task 3

AI & the Web, winter term 2024/2025

## Running the code on your development server

1. Change parameter variables in client.py (HUB_AUTHKEY, HUB_URL) and channel.py (HUB_URL, HUB_AUTHKEY, CHANNEL_ENDPOINT, CHANNEL_FILE) for your use case 

2. Create and activate a virtual environment, install everything from requirements.txt

3. Run hub

    > python hub.py

4. Run the channel server (different shell)

    > python channel.py

5. Register the channel server with the hub (another different shell)

    > flask --app channel.py register
    
6. Start the flask client (new shell or shell from 4.) 

    > python client.py

7. Open the client, link is displayed after client start (e.g., http://localhost:5005)

8. Start the React client


# Running on the university server

Client available at http://vm322.rz.uni-osnabrueck.de/u058/hub_channel/client.wsgi/

Channel available at http://vm322.rz.uni-osnabrueck.de/u058/hub_channel/channel.wsgi/