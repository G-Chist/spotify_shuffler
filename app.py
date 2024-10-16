import requests  # Importing requests library to make HTTP requests
import urllib.parse  # Importing urllib to handle URL encoding
from flask import Flask, request, redirect, session, render_template, url_for  # Importing Flask-related functions
from keys import client_ID, client_secret, secret_flask  # Importing sensitive keys from a separate module
from random import randint  # Importing randint to generate random numbers for shuffling

# Spotify API credentials
CLIENT_ID = client_ID  # Set the client ID from keys
CLIENT_SECRET = client_secret  # Set the client secret from keys
REDIRECT_URI = 'http://localhost:5000/callback'  # Define the redirect URI after authorization
SCOPE = 'playlist-modify-public playlist-modify-private playlist-read-private'  # Define the scopes for API access

app = Flask(__name__)  # Create a Flask application instance
app.secret_key = secret_flask  # Set the secret key for session management


def reorder_tracks(access_token, playlist_id, range_start, insert_before):
    """
    Reorder tracks in a Spotify playlist.

    :param access_token: OAuth token for Spotify API access.
    :param playlist_id: ID of the playlist to modify.
    :param range_start: The current position of the track to be moved.
    :param insert_before: The new position where the track will be inserted.
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # Define the API endpoint for updating tracks

    headers = {
        'Authorization': f'Bearer {access_token}',  # Set the Authorization header with the access token
        'Content-Type': 'application/json'  # Set the Content-Type header for JSON data
    }

    # Data for reordering tracks
    data = {
        'range_start': range_start,  # Index of the track to move
        'insert_before': insert_before  # New position to move the track to
    }

    response = requests.put(url, headers=headers, json=data)  # Send the PUT request to reorder tracks


# Authorization URL
@app.route('/')  # Define the route for the main page
def authorize():
    auth_url = 'https://accounts.spotify.com/authorize'  # Spotify's authorization URL
    params = {
        'client_id': CLIENT_ID,  # Client ID for your Spotify app
        'response_type': 'code',  # Specify that we want an authorization code
        'redirect_uri': REDIRECT_URI,  # URI to redirect to after authorization
        'scope': SCOPE  # Scopes that define the access permissions
    }
    auth_request = f"{auth_url}?{urllib.parse.urlencode(params)}"  # Create the full authorization URL
    return redirect(auth_request)  # Redirect the user to the authorization page


# Handle Spotify Callback
@app.route('/callback')  # Define the callback route for Spotify to redirect to
def callback():
    code = request.args.get('code')  # Get the authorization code from the URL parameters
    token_url = 'https://accounts.spotify.com/api/token'  # URL to request access tokens
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}  # Header for form data
    data = {
        'grant_type': 'authorization_code',  # Specify the grant type for the token request
        'code': code,  # The authorization code received
        'redirect_uri': REDIRECT_URI,  # Same redirect URI used in the authorization request
        'client_id': CLIENT_ID,  # Client ID for your Spotify app
        'client_secret': CLIENT_SECRET  # Client secret for your Spotify app
    }
    response = requests.post(token_url, headers=headers, data=data)  # Request access token
    session['access_token'] = response.json().get('access_token')  # Store the access token in the session
    return redirect('/playlists')  # Redirect to the playlists page


# Get User Playlists
@app.route("/playlists")  # Define the route to view user playlists
def playlists():
    access_token = session.get('access_token')  # Retrieve the access token from the session
    headers = {'Authorization': f'Bearer {access_token}'}  # Set the Authorization header

    # Fetch user playlists
    response = requests.get('https://api.spotify.com/v1/me/playlists', headers=headers)  # Request the user's playlists
    playlists_data = response.json().get('items', [])  # Parse the response to get playlists

    # Fetch the authenticated user's Spotify ID
    user_info_response = requests.get('https://api.spotify.com/v1/me', headers=headers)  # Request user info
    user_id = user_info_response.json().get('id')  # Extract the user's ID from the response

    # Format playlists with name, image, and ID
    playlists_display_format = [
        {
            'id': playlist["id"],  # Include the playlist ID
            'name': playlist["name"],  # Include the playlist name
            'image': playlist["images"][0]["url"] if playlist["images"] else None  # Include the first image or None
        }
        for playlist in playlists_data if playlist["owner"]["id"] == user_id  # Filter by user-owned playlists
    ]

    return render_template("playlists.html", playlists=playlists_display_format)  # Render the playlists in the HTML


# Route to handle button click (receives playlist ID)
@app.route('/shuffle_playlist/<playlist_id>', methods=['GET'])  # Define the route to shuffle a playlist
def shuffle_playlist(playlist_id):
    access_token = session.get('access_token')  # Retrieve the access token from the session
    headers = {'Authorization': f'Bearer {access_token}'}  # Set the Authorization header
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'  # Define the URL to get playlist details

    response = requests.get(url, headers=headers)  # Request the playlist details

    if response.status_code == 200:  # Check if the request was successful
        # print(f"Shuffling playlist with ID: {playlist_id}")
        playlist_data = response.json()  # Parse the response to get playlist data
        # The number of tracks in the playlist
        num_tracks = playlist_data['tracks']['total']  # Get the total number of tracks in the playlist
        # print(f"Number of tracks: {num_tracks}")

        # Shuffle using Fisher-Yates
        for i in range(num_tracks - 1, 0, -1):  # Loop to shuffle tracks
            j = randint(0, i)  # Generate a random index from 0 to i
            reorder_tracks(access_token, playlist_id, i, j)  # Move the track from i to j

    return redirect(url_for('playlists'))  # Redirect back to the playlists page


if __name__ == '__main__':
    app.run(port=5000)  # Run the Flask application on port 5000
