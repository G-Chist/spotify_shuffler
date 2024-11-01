import requests  # Importing requests library to make HTTP requests
import urllib.parse  # Importing urllib to handle URL encoding
from flask import Flask, request, redirect, session, render_template, url_for, flash  # Flask-related functions
from keys import client_ID, client_secret, secret_flask  # Importing sensitive keys from a separate module
from random import randint  # Importing randint to generate random numbers for shuffling
import time  # Importing time to keep track of how long it takes to shuffle
from list_shuffler import fisher_yates_shuffle  # Import list shuffling function

CLIENT_ID = client_ID  # Set the client ID from keys
CLIENT_SECRET = client_secret  # Set the client secret from keys
REDIRECT_URI = 'http://localhost:5000/callback'  # Define the redirect URI after authorization
SCOPE = 'playlist-modify-public playlist-modify-private playlist-read-private'  # Define the scopes for API access

app = Flask(__name__)  # Create a Flask application instance
app.secret_key = secret_flask  # Set the secret key for session management


def has_dupes(arr, element):
    return arr.count(element) >= 2


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def chunk_array(arr, chunk_size=100):
    """Split an array into chunks of specified size.

    :param arr: Array to split into chunks.
    :param chunk_size: Chunk size.
    """
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]


def get_track_details(uri_or_id, access_token):
    # Check if input is a URI; if so, extract the track ID
    if uri_or_id.startswith("spotify:track:"):
        track_id = uri_or_id.split(":")[-1]
    else:
        track_id = uri_or_id  # Assume it's already a track ID

    url = f'https://api.spotify.com/v1/tracks/{track_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        track_data = response.json()
        track_name = track_data['name']
        track_length = track_data['duration_ms']  # Length in milliseconds
        artist_name = track_data['artists'][0]['name']  # Primary artist name

        # Convert duration from milliseconds to seconds
        track_length_seconds = track_length / 1000

        return {
            'name': track_name,
            'artist': artist_name,
            'length_ms': track_length,
            'length_seconds': track_length_seconds
        }
    else:
        # print("Error:", response.status_code, response.json())
        return None


def get_tracks(playlist_id, headers):
    """Retrieve all tracks from the playlist.

    :param playlist_id: ID of the playlist to modify.
    :param headers: Request headers.
    :return: List of all tracks in the playlist.
    """
    tracks = []  # Initialize an empty list to store tracks
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # Base URL for the request

    while url:  # Continue looping while there is a URL to request
        response = requests.get(url, headers=headers)  # Make the GET request
        if response.status_code != 200:
            raise Exception(f"Failed to get tracks: {response.status_code} {response.json()}")

        data = response.json()  # Parse the JSON response
        tracks.extend(data.get('items', []))  # Add the current items to the tracks list
        url = data.get('next')  # Update the URL to the next page of results

    return tracks  # Return the complete list of tracks


def add_tracks(access_token, playlist_id, tracks_list):
    """
    Add given tracks to a Spotify playlist.

    :param access_token: OAuth token for Spotify API access.
    :param playlist_id: ID of the playlist to modify.
    :param tracks_list: List of tracks to add to the playlist.
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # Spotify API endpoint for adding tracks

    len_tracks = len(tracks_list)  # Get the size of the list of tracks to add

    headers = {
        'Authorization': f'Bearer {access_token}',  # Set Authorization header with the access token
        'Content-Type': 'application/json'  # Set Content-Type for JSON data
    }

    tracks_list_chunks = chunk_array(arr=tracks_list, chunk_size=100)  # Chunk array to limit tracks to 100 per request

    position_tracker = 0  # Variable to keep track of position to add tracks to
    for chunk in tracks_list_chunks:
        track_uris = [item['track']['uri'] for item in chunk]  # Limit to 100 per request
        data = {'uris': track_uris, 'position': position_tracker}  # Prepare data to add

        response = requests.post(url, headers=headers, json=data)  # Send POST request
        if response.status_code != 201:
            raise Exception(f"Failed to add tracks: {response.status_code} {response.json()}")

        len_tracks -= 100  # Keep track of number of tracks to add
        position_tracker += 100  # Update position


def remove_all_tracks(access_token, playlist_id):
    """
    Remove all tracks from a Spotify playlist.

    :param access_token: OAuth token for Spotify API access.
    :param playlist_id: ID of the playlist to modify.
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"  # Spotify API endpoint for removing tracks

    headers = {
        'Authorization': f'Bearer {access_token}',  # Set Authorization header with the access token
        'Content-Type': 'application/json'  # Set Content-Type for JSON data
    }

    tracks = get_tracks(playlist_id=playlist_id, headers=headers)  # Fetch the initial set of tracks

    while tracks:  # Continue until all tracks are removed
        track_uris = [{'uri': item['track']['uri']} for item in tracks[:100]]  # Limit to 100 per request
        data = {'tracks': track_uris}  # Prepare data for removal

        response = requests.delete(url, headers=headers, json=data)  # Send DELETE request
        if response.status_code != 200:
            raise Exception(f"Failed to remove tracks: {response.status_code} {response.json()}")

        # print(f"Removed {len(track_uris)} tracks.")  # Log the removal progress
        tracks = get_tracks(playlist_id=playlist_id, headers=headers)  # Fetch remaining tracks

    # print("All tracks have been removed from the playlist.")


# DOES NOT WORK YET
def remove_dupe_tracks(access_token, playlist_id):
    """
    Remove all duplicate tracks from a Spotify playlist based on track name, artist, and length.

    :param access_token: OAuth token for Spotify API access.
    :param playlist_id: ID of the playlist to modify.
    """
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Fetch the initial set of tracks
    tracks = get_tracks(playlist_id=playlist_id, headers=headers)
    num_removed = 0

    return num_removed


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


# Authorization URL (default)
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
            'image': playlist["images"][0]["url"] if playlist["images"] else None,  # Include the first image or None
            'length': playlist["tracks"]["total"],  # Include the length of the playlist
            'estimated_shuffle_time': int(int(playlist["tracks"]["total"]) * 0.2)  # Include estimated shuffle time
        }
        for playlist in playlists_data if playlist["owner"]["id"] == user_id  # Filter by user-owned playlists
    ]

    return render_template("playlists.html", playlists=playlists_display_format)  # Render the playlists in the HTML


# OUTDATED: Route to handle shuffle button click (receives playlist ID)
@app.route('/shuffle_playlist/<playlist_id>', methods=['GET'])  # Define the route to shuffle a playlist
def shuffle_playlist(playlist_id):
    shuffle_start_time = time.time()  # Get time (in seconds) when shuffling started
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
        # Time to shuffle per track: ~0.2 seconds

    shuffle_end_time = time.time()  # Get time (in seconds) when shuffling ended
    shuffle_total_time = f"{shuffle_end_time - shuffle_start_time:.2f}"  # Total shuffling time, 2 digits after point

    flash(f"Playlist shuffle time: {shuffle_total_time} seconds")  # Return message containing shuffle time
    return redirect(url_for('playlists'))  # Redirect back to the playlists page


# Route to handle fast shuffle button click (receives playlist ID)
@app.route('/fast_shuffle_playlist/<playlist_id>', methods=['GET'])  # Define the route to shuffle a playlist
def fast_shuffle_playlist(playlist_id):
    shuffle_start_time = time.time()  # Get time (in seconds) when shuffling started
    access_token = session.get('access_token')  # Retrieve the access token from the session
    headers = {'Authorization': f'Bearer {access_token}'}  # Set the Authorization header
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'  # Define the URL to get playlist details

    response = requests.get(url, headers=headers)  # Request the playlist details

    if response.status_code == 200:  # Check if the request was successful
        track_list = get_tracks(playlist_id=playlist_id, headers=headers)  # Get tracks from playlist
        shuffled_track_list = fisher_yates_shuffle(track_list)  # Shuffle track list
        remove_all_tracks(access_token=access_token, playlist_id=playlist_id)  # Remove all tracks from the playlist
        add_tracks(access_token=access_token, playlist_id=playlist_id, tracks_list=shuffled_track_list)  # Add tracks to the playlist

        shuffle_end_time = time.time()  # Get time (in seconds) when shuffling ended
        shuffle_total_time = f"{shuffle_end_time - shuffle_start_time:.2f}"  # Total shuffling time, 2 digits after point

        flash(f"Playlist shuffle time: {shuffle_total_time} seconds")  # Return message containing shuffle time

    return redirect(url_for('playlists'))  # Redirect back to the playlists page


@app.route('/delete_duplicate_tracks/<playlist_id>', methods=['GET'])  # Define the route to shuffle a playlist
def delete_duplicate_tracks(playlist_id):
    delete_start_time = time.time()  # Get time (in seconds) when function started
    access_token = session.get('access_token')  # Retrieve the access token from the session
    headers = {'Authorization': f'Bearer {access_token}'}  # Set the Authorization header
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}'  # Define the URL to get playlist details

    response = requests.get(url, headers=headers)  # Request the playlist details

    if response.status_code == 200:  # Check if the request was successful
        delete_end_time = time.time()  # Get time (in seconds) when function ended
        delete_total_time = f"{delete_end_time - delete_start_time:.2f}"  # Total deleting time, 2 digits after point
        removed_count = remove_dupe_tracks(access_token=access_token, playlist_id=playlist_id)  # Remove duplicate tracks
        flash(f"Deleted {removed_count} duplicate tracks in {delete_total_time} seconds")  # Return message containing time and count

    return redirect(url_for('playlists'))  # Redirect back to the playlists page


if __name__ == '__main__':
    app.run(port=5000)  # Run the Flask application on port 5000
