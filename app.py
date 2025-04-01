from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import json
import logging
import re
import random
import traceback
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Spotify OAuth setup
SPOTIFY_SCOPE = 'user-library-read playlist-read-private user-read-private user-read-email user-top-read'
sp_oauth = SpotifyOAuth(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    scope=SPOTIFY_SCOPE
)

# List of valid Spotify genres we can use for recommendations
VALID_SPOTIFY_GENRES = [
    "acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "anime", 
    "black-metal", "bluegrass", "blues", "brazil", "breakbeat", "british", 
    "cantopop", "chicago-house", "children", "chill", "classical", "club", 
    "comedy", "country", "dance", "dancehall", "death-metal", "deep-house", 
    "detroit-techno", "disco", "disney", "drum-and-bass", "dub", "dubstep", 
    "edm", "electro", "electronic", "emo", "folk", "forro", "french", "funk", 
    "garage", "german", "gospel", "goth", "grindcore", "groove", "grunge", 
    "guitar", "happy", "hard-rock", "hardcore", "hardstyle", "heavy-metal", 
    "hip-hop", "house", "idm", "indian", "indie", "indie-pop", "industrial", 
    "iranian", "j-dance", "j-idol", "j-pop", "j-rock", "jazz", "k-pop", "kids", 
    "latin", "latino", "malay", "mandopop", "metal", "metalcore", "minimal-techno", 
    "mpb", "new-age", "opera", "pagode", "party", "piano", "pop", "pop-film", 
    "power-pop", "progressive-house", "psych-rock", "punk", "punk-rock", "r-n-b", 
    "reggae", "reggaeton", "rock", "rock-n-roll", "rockabilly", "romance", "sad", 
    "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter", "ska", 
    "sleep", "songwriter", "soul", "spanish", "study", "summer", "swedish", "synth-pop", 
    "tango", "techno", "trance", "trip-hop", "turkish", "work-out", "world-music"
]

# Audio features for different moods to create more diverse recommendations
MOOD_FEATURES = {
    "happy": {
        "min_valence": 0.7,
        "min_energy": 0.7,
        "target_tempo": 120,
        "genres": ["happy", "pop", "dance", "disco"]
    },
    "sad": {
        "max_valence": 0.4,
        "max_energy": 0.4, 
        "target_tempo": 90,
        "genres": ["sad", "indie", "singer-songwriter", "piano"]
    },
    "relaxed": {
        "max_energy": 0.4,
        "target_instrumentalness": 0.5,
        "genres": ["ambient", "chill", "study", "piano"]
    },
    "energetic": {
        "min_energy": 0.8,
        "min_tempo": 125,
        "genres": ["work-out", "dance", "edm", "rock"]
    },
    "focused": {
        "target_instrumentalness": 0.7,
        "max_speechiness": 0.1,
        "genres": ["study", "classical", "ambient", "piano"]
    },
    "angry": {
        "min_energy": 0.7,
        "max_valence": 0.4,
        "target_tempo": 140,
        "genres": ["rock", "metal", "hard-rock", "alt-rock"]
    },
    "nostalgic": {
        "target_acousticness": 0.6,
        "genres": ["rock-n-roll", "blues", "jazz", "soul"]
    }
}

# Hardcoded backup tracks by mood (as a last resort)
BACKUP_TRACKS_BY_MOOD = {
    "happy": [
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2736acc3a55cbab6f9ae5505aa4"}]},
            "artists": [{"name": "Taylor Swift"}],
            "name": "Shake It Off",
            "external_urls": {"spotify": "https://open.spotify.com/track/0cqRj7pUJDkTCEsJkx8snD"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96"}]},
            "artists": [{"name": "Ed Sheeran"}],
            "name": "Shape of You",
            "external_urls": {"spotify": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273c5148520a59be191eea29985"}]},
            "artists": [{"name": "Pharrell Williams"}],
            "name": "Happy",
            "external_urls": {"spotify": "https://open.spotify.com/track/60nZcImufyMA1MKQY3dcCO"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2739e1cfc756886ac782e363d79"}]},
            "artists": [{"name": "Justin Timberlake"}],
            "name": "Can't Stop The Feeling!",
            "external_urls": {"spotify": "https://open.spotify.com/track/1WkMMavIMc4JZ8cfMmxHkI"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273f46b9d202509a8f7384b90de"}]},
            "artists": [{"name": "Bruno Mars"}],
            "name": "Uptown Funk",
            "external_urls": {"spotify": "https://open.spotify.com/track/32OlwWuMpZ6b0aN2RZOeMS"}
        }
    ],
    "sad": [
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2735ef878a782c987d38d82b605"}]},
            "artists": [{"name": "Adele"}],
            "name": "Someone Like You",
            "external_urls": {"spotify": "https://open.spotify.com/track/1T3Sdf6j5S5HXxyc9dyD5W"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273e8b066f70c206551210d902b"}]},
            "artists": [{"name": "Billie Eilish"}],
            "name": "when the party's over",
            "external_urls": {"spotify": "https://open.spotify.com/track/43zdsphuZLzwA9k4DJhU0I"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2734a5584794d8a1e9f911f3977"}]},
            "artists": [{"name": "Lewis Capaldi"}],
            "name": "Someone You Loved",
            "external_urls": {"spotify": "https://open.spotify.com/track/7qEHsqek33rTcFNT9PFqLf"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2736c9e3e57dc88c33fde5379a2"}]},
            "artists": [{"name": "Coldplay"}],
            "name": "Fix You",
            "external_urls": {"spotify": "https://open.spotify.com/track/7LVHVU3tWfcxj5aiPFEW4Q"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273e787cffec20aa2a396a61647"}]},
            "artists": [{"name": "James Bay"}],
            "name": "Let It Go",
            "external_urls": {"spotify": "https://open.spotify.com/track/13HVjjWUZFaWilh2QUJKsP"}
        }
    ],
    "relaxed": [
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273a40e3897b8aa1be97bf5992f"}]},
            "artists": [{"name": "Bon Iver"}],
            "name": "Holocene",
            "external_urls": {"spotify": "https://open.spotify.com/track/3TnoWk9cUH4jfZ07L8feSr"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273c79b600289a80aaef74d155d"}]},
            "artists": [{"name": "Sigur Rós"}],
            "name": "Hoppípolla",
            "external_urls": {"spotify": "https://open.spotify.com/track/6eTGxxQxiTFE6LfZHC33Wm"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273ce85c93e88cd5bbf98cc5366"}]},
            "artists": [{"name": "Brian Eno"}],
            "name": "1/1",
            "external_urls": {"spotify": "https://open.spotify.com/track/7M4YXpgGQbcqZVG4ZF0Z2Q"}
        }
    ],
    "energetic": [
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b27358ecb3e5ec3bbef70ee09a43"}]},
            "artists": [{"name": "The Weeknd"}],
            "name": "Blinding Lights",
            "external_urls": {"spotify": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2732f44aec83b20e40f3baef73c"}]},
            "artists": [{"name": "Dua Lipa"}],
            "name": "Don't Start Now",
            "external_urls": {"spotify": "https://open.spotify.com/track/3PfIrDoz19wz7qK7tYeu62"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273e787cffec20aa2a396a61647"}]},
            "artists": [{"name": "Daft Punk"}],
            "name": "Get Lucky",
            "external_urls": {"spotify": "https://open.spotify.com/track/2Foc5Q5nqNiosCNqttzHof"}
        }
    ],
    "default": [
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96"}]},
            "artists": [{"name": "Ed Sheeran"}],
            "name": "Shape of You",
            "external_urls": {"spotify": "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b273e8b066f70c206551210d902b"}]},
            "artists": [{"name": "Billie Eilish"}],
            "name": "bad guy",
            "external_urls": {"spotify": "https://open.spotify.com/track/2Fxmhks0bxGSBdJ92vM42m"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b27358ecb3e5ec3bbef70ee09a43"}]},
            "artists": [{"name": "The Weeknd"}],
            "name": "Blinding Lights",
            "external_urls": {"spotify": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2732f44aec83b20e40f3baef73c"}]},
            "artists": [{"name": "Dua Lipa"}],
            "name": "Don't Start Now",
            "external_urls": {"spotify": "https://open.spotify.com/track/3PfIrDoz19wz7qK7tYeu62"}
        },
        {
            "album": {"images": [{"url": "https://i.scdn.co/image/ab67616d0000b2736acc3a55cbab6f9ae5505aa4"}]},
            "artists": [{"name": "Taylor Swift"}],
            "name": "Shake It Off",
            "external_urls": {"spotify": "https://open.spotify.com/track/0cqRj7pUJDkTCEsJkx8snD"}
        }
    ]
}

# Define a simple mood analyzer function
def analyze_mood_text(text):
    """Simple rule-based mood analyzer as a fallback for the Gemini API"""
    text = text.lower()
    
    # Define mood keywords and their corresponding analysis and genres
    # Map our moods to valid Spotify genres
    mood_map = {
        'happy': {
            'analysis': 'You seem happy and upbeat! Your mood is positive and energetic.',
            'genre': 'happy',
            'mood_category': 'happy'
        },
        'sad': {
            'analysis': 'You seem to be feeling down or melancholic. Music can help lift your spirits.',
            'genre': 'sad',
            'mood_category': 'sad'
        },
        'angry': {
            'analysis': 'Your text suggests feelings of frustration or anger. Some energizing music might help.',
            'genre': 'rock',
            'mood_category': 'angry'
        },
        'tired': {
            'analysis': 'You sound tired or fatigued. Some relaxing music could be just what you need.',
            'genre': 'chill',
            'mood_category': 'relaxed'
        },
        'excited': {
            'analysis': 'You seem very excited and enthusiastic! Some upbeat music would match your energy.',
            'genre': 'dance',
            'mood_category': 'energetic'
        },
        'relaxed': {
            'analysis': 'You appear to be in a calm, relaxed state. Some smooth music would complement this well.',
            'genre': 'ambient',
            'mood_category': 'relaxed'
        },
        'stressed': {
            'analysis': 'You seem to be experiencing stress. Some calming music might help you unwind.',
            'genre': 'classical',
            'mood_category': 'relaxed'
        },
        'bored': {
            'analysis': 'You sound a bit bored or understimulated. Some engaging music could help.',
            'genre': 'pop',
            'mood_category': 'energetic'
        },
        'nostalgic': {
            'analysis': 'Your words have a nostalgic quality. Music that reminds you of good times might resonate.',
            'genre': 'rock-n-roll',
            'mood_category': 'nostalgic'
        },
        'focused': {
            'analysis': 'You seem to be in a focused state. Some concentration-enhancing music could help maintain this.',
            'genre': 'study',
            'mood_category': 'focused'
        },
        'sleepy': {
            'analysis': 'You sound sleepy or drowsy. Some gentle music could help you relax further.',
            'genre': 'sleep',
            'mood_category': 'relaxed'
        },
        'energetic': {
            'analysis': 'Your text suggests high energy levels. Some upbeat music would match this well.',
            'genre': 'work-out',
            'mood_category': 'energetic'
        },
        'calm': {
            'analysis': 'You seem calm and collected. Some gentle music would complement this mood.',
            'genre': 'chill',
            'mood_category': 'relaxed'
        },
        'anxious': {
            'analysis': 'Your text suggests some anxiety or worry. Some calming music might help you relax.',
            'genre': 'ambient',
            'mood_category': 'relaxed'
        },
        'love': {
            'analysis': 'Your words suggest feelings of love or romance. Some heartfelt music would match this mood.',
            'genre': 'romance',
            'mood_category': 'happy'
        }
    }
    
    # Check for mood keywords in the text
    matched_moods = []
    for mood in mood_map:
        if re.search(r'\b' + mood + r'\b', text):  # Match whole words only
            matched_moods.append(mood)
    
    # If no direct mood words found, try to infer from common phrases
    if not matched_moods:
        if any(phrase in text for phrase in ["feeling good", "great day", "wonderful", "amazing"]):
            matched_moods.append("happy")
        elif any(phrase in text for phrase in ["feeling down", "not great", "terrible", "worst"]):
            matched_moods.append("sad")
        elif any(phrase in text for phrase in ["need to focus", "concentrate", "study"]):
            matched_moods.append("focused")
        elif any(phrase in text for phrase in ["can't sleep", "need to relax", "wind down"]):
            matched_moods.append("relaxed")
        elif any(phrase in text for phrase in ["need energy", "workout", "exercise"]):
            matched_moods.append("energetic")
        else:
            # Default if no mood is detected - pick from a few safe genres
            safe_moods = ["happy", "relaxed", "energetic", "focused"]
            selected = random.choice(safe_moods)
            return {
                'analysis': 'I analyzed your text and will recommend some music that might match your current state.',
                'genre': mood_map[selected]['genre'],
                'mood_category': mood_map[selected]['mood_category']
            }
    
    # Use the first matched mood
    chosen_mood = matched_moods[0]
    return mood_map[chosen_mood]

# Function to get a fresh access token if needed
def get_spotify_client():
    """Get a fresh Spotify client with valid access token"""
    if 'token_info' not in session:
        logger.error("No token_info in session")
        return None
    
    token_info = session['token_info']
    
    # Check if token is expired and refresh if needed
    try:
        if sp_oauth.is_token_expired(token_info):
            logger.info("Token expired, refreshing...")
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
            logger.info("Token refreshed successfully")
        
        # Print token details (excluding sensitive parts)
        token_preview = f"...{token_info['access_token'][-8:]}" if token_info.get('access_token') else "None"
        logger.debug(f"Using access token ending with: {token_preview}")
        
        return Spotify(auth=token_info['access_token'])
    except Exception as e:
        logger.error(f"Error in get_spotify_client: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    try:
        code = request.args.get('code')
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        return f"Error during Spotify authentication: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    try:
        sp = get_spotify_client()
        user_info = sp.current_user()
        return render_template('dashboard.html', user=user_info)
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        session.clear()  # Clear invalid session
        return redirect(url_for('login'))

@app.route('/analyze_mood', methods=['POST'])
def analyze_mood():
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    text = request.json.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        # Use our mood analyzer
        logger.debug(f"Analyzing mood text: {text}")
        mood_result = analyze_mood_text(text)
        mood_analysis = mood_result['analysis']
        genre = mood_result['genre']
        mood_category = mood_result['mood_category']
        
        logger.debug(f"Mood analysis result: {mood_analysis}")
        logger.debug(f"Selected genre: {genre}")
        logger.debug(f"Mood category: {mood_category}")
        
        # Get a fresh Spotify client
        sp = get_spotify_client()
        if not sp:
            logger.error("Failed to get Spotify client - clearing session and returning to login")
            session.clear()
            return jsonify({'error': 'Spotify authentication expired, please log in again'}), 401
        
        # Verify the Spotify client is working before proceeding
        try:
            # Simple API call to test connectivity
            logger.debug("Testing Spotify API connectivity...")
            user_info = sp.current_user()
            logger.debug(f"Spotify API test successful. Connected as: {user_info['display_name']}")
        except Exception as e:
            logger.error(f"Spotify API connectivity test failed: {str(e)}")
            # If it's an authentication error, clear session
            if "authentication" in str(e).lower() or "unauthorized" in str(e).lower() or "token" in str(e).lower():
                session.clear()
                return jsonify({'error': 'Spotify authentication failed, please log in again'}), 401
            # Otherwise continue with fallbacks
        
        # Try multiple methods to get recommendations, with increasing fallbacks
        recommendations = None
        source = "unknown"  # Track the source of recommendations
        
        # Method 1: Try advanced recommendations with audio features based on mood
        try:
            logger.debug(f"Trying advanced recommendations for mood: {mood_category}")
            
            # Get audio features for this mood if available
            audio_features = {}
            if mood_category in MOOD_FEATURES:
                audio_features = MOOD_FEATURES[mood_category].copy()
                # Remove the genres key to use separately
                genres = audio_features.pop('genres', [genre])
            else:
                genres = [genre]
            
            # Ensure we're using valid genres (take up to 2)
            valid_genres = [g for g in genres if g in VALID_SPOTIFY_GENRES][:2]
            if not valid_genres:
                valid_genres = ["pop"]  # Default fallback
            
            logger.debug(f"Using genres: {valid_genres} with audio features: {audio_features}")
            
            # Get available genre seeds from Spotify
            try:
                available_genres = sp.recommendation_genre_seeds()
                logger.debug(f"Available Spotify genres: {available_genres}")
                
                # Verify our genres are actually in the list
                spotify_genres = available_genres.get('genres', [])
                for genre in valid_genres:
                    if genre not in spotify_genres:
                        logger.warning(f"Genre '{genre}' not in Spotify's available genres!")
                
                # Ensure we're using actual available genres
                valid_genres = [g for g in valid_genres if g in spotify_genres]
                if not valid_genres:
                    valid_genres = ["pop"]
                    logger.warning("No valid genres found, falling back to 'pop'")
            except Exception as genre_err:
                logger.warning(f"Failed to get genre seeds: {str(genre_err)}")
            
            # Slightly randomize audio features to get more diverse recommendations
            if 'target_tempo' in audio_features:
                audio_features['target_tempo'] += random.randint(-10, 10)
            if 'min_energy' in audio_features:
                audio_features['min_energy'] = max(0.0, min(1.0, audio_features['min_energy'] + random.uniform(-0.1, 0.1)))
            if 'max_energy' in audio_features:
                audio_features['max_energy'] = max(0.0, min(1.0, audio_features['max_energy'] + random.uniform(-0.1, 0.1)))
            if 'min_valence' in audio_features:
                audio_features['min_valence'] = max(0.0, min(1.0, audio_features['min_valence'] + random.uniform(-0.1, 0.1)))
            if 'max_valence' in audio_features:
                audio_features['max_valence'] = max(0.0, min(1.0, audio_features['max_valence'] + random.uniform(-0.1, 0.1)))
            
            # Try up to 3 different sets of recommendations to get more variety
            all_tracks = []
            attempt_count = 0
            
            # Make 5-6 attempts to gather more tracks
            max_attempts = 5
            while len(all_tracks) < 12 and attempt_count < max_attempts:
                # Add randomness by using different genres from our valid set on each attempt
                attempt_count += 1
                
                # If we have multiple attempts, shuffle audio features slightly each time
                if attempt_count > 1:
                    if 'target_tempo' in audio_features:
                        audio_features['target_tempo'] += random.randint(-15, 15)
                    if 'min_energy' in audio_features:
                        audio_features['min_energy'] = max(0.0, min(1.0, audio_features['min_energy'] + random.uniform(-0.15, 0.15)))
                    if 'max_energy' in audio_features:
                        audio_features['max_energy'] = max(0.0, min(1.0, audio_features['max_energy'] + random.uniform(-0.15, 0.15)))
                    if 'min_valence' in audio_features:
                        audio_features['min_valence'] = max(0.0, min(1.0, audio_features['min_valence'] + random.uniform(-0.15, 0.15)))
                    if 'max_valence' in audio_features:
                        audio_features['max_valence'] = max(0.0, min(1.0, audio_features['max_valence'] + random.uniform(-0.15, 0.15)))
                
                # Get recommendations with specific audio features for this mood
                logger.debug(f"Attempt {attempt_count}: Calling Spotify recommendations API with genres={valid_genres}, features={audio_features}")
                current_recs = sp.recommendations(
                    seed_genres=valid_genres,
                    limit=20,  # Request more than we need to filter
                    **audio_features
                )
                
                # Verify we got actual tracks
                if current_recs and 'tracks' in current_recs and current_recs['tracks']:
                    # Filter tracks with proper images
                    filtered_tracks = []
                    for track in current_recs['tracks']:
                        # Check if track has valid album art
                        has_valid_image = (
                            track.get('album') and 
                            track['album'].get('images') and 
                            len(track['album']['images']) > 0 and
                            'url' in track['album']['images'][0] and
                            not track['album']['images'][0]['url'].endswith('dog.jpg')  # Filter out dog image
                        )
                        
                        if has_valid_image:
                            # Check if track is not already in our collection
                            track_id = track.get('id')
                            if track_id and not any(t.get('id') == track_id for t in all_tracks):
                                filtered_tracks.append(track)
                    
                    logger.debug(f"Attempt {attempt_count}: Found {len(filtered_tracks)} valid tracks")
                    all_tracks.extend(filtered_tracks)
                    
                    # If we have enough tracks, break out
                    if len(all_tracks) >= 12:
                        break
                    
                    # Otherwise, adjust our parameters for the next attempt
                    if valid_genres and len(valid_genres) > 1:
                        # Shuffle the genres to get different recommendations
                        random.shuffle(valid_genres)
                
                # Only make additional attempts if we need more tracks
                if len(all_tracks) >= 12:
                    break
                
                # If we're making multiple attempts, try a different approach
                if attempt_count == 3 and len(all_tracks) < 8:
                    # Try with a completely different genre for more variety
                    different_genres = ["pop", "rock", "indie", "dance", "electronic", "hip-hop", "jazz", "classical"]
                    random.shuffle(different_genres)
                    valid_genres = different_genres[:2]
                
                # Wait briefly between attempts to avoid rate limiting
                time.sleep(0.1)
            
            # Take the tracks or whatever we got
            if all_tracks:
                recommendations = {'tracks': all_tracks[:12]}
                source = "spotify_advanced"
                logger.debug(f"Successfully got {len(all_tracks[:12])} advanced recommendations")
            else:
                raise Exception("No valid tracks found after multiple attempts")
        except Exception as e:
            logger.warning(f"Advanced recommendations failed: {str(e)}")
            traceback.print_exc()
            
            # Method 2: Try with user's top tracks for diversity
            try:
                logger.debug("Trying to get recommendations based on user's top tracks")
                top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')
                
                if top_tracks and 'items' in top_tracks and top_tracks['items']:
                    # Use track IDs from user's top tracks as seeds
                    track_ids = [track['id'] for track in top_tracks['items'][:3]]
                    if track_ids:
                        # Make multiple calls with different seeds for variety
                        all_tracks = []
                        for i in range(min(3, len(track_ids))):
                            seed_id = track_ids[i]
                            top_based_recommendations = sp.recommendations(
                                seed_tracks=[seed_id],
                                limit=10
                            )
                            
                            if top_based_recommendations and 'tracks' in top_based_recommendations:
                                # Filter out tracks with bad images
                                filtered_tracks = [
                                    t for t in top_based_recommendations['tracks'] 
                                    if t.get('album') and t['album'].get('images') and 
                                    len(t['album']['images']) > 0 and
                                    not t['album']['images'][0]['url'].endswith('dog.jpg')
                                ]
                                
                                # Add unique tracks
                                for track in filtered_tracks:
                                    track_id = track.get('id')
                                    if track_id and not any(t.get('id') == track_id for t in all_tracks):
                                        all_tracks.append(track)
                                        
                        if all_tracks:
                            recommendations = {'tracks': all_tracks[:12]}
                            source = "spotify_user_top_tracks"
                            logger.debug(f"Successfully got {len(all_tracks[:12])} recommendations based on user's top tracks")
                        else:
                            raise Exception("No valid tracks after filtering user top tracks recommendations")
                    else:
                        raise Exception("No valid track IDs found in user's top tracks")
                else:
                    logger.warning("No user top tracks found")
                    raise Exception("No top tracks found")
            except Exception as e2:
                logger.warning(f"User top tracks approach failed: {str(e2)}")
                
                # Method 3: Try simpler genre-based recommendations
                try:
                    logger.debug("Trying simple genre-based recommendations")
                    
                    # Try with popular genres but pick more random ones for variety
                    popular_genres = ["pop", "rock", "hip-hop", "dance", "electronic", "indie", "r-n-b", "jazz", "classical"]
                    random.shuffle(popular_genres)
                    
                    # Make multiple calls with different genre combinations
                    all_tracks = []
                    for i in range(3):  # Try 3 different genre combinations
                        selected_genres = popular_genres[i*3:(i+1)*3]
                        if not selected_genres:
                            break
                            
                        logger.debug(f"Using popular genres '{selected_genres}' for simple recommendations")
                        
                        # Fall back to a simpler request with minimal parameters
                        simple_recommendations = sp.recommendations(seed_genres=selected_genres, limit=10)
                        
                        # Verify we got actual tracks with good images
                        if simple_recommendations and 'tracks' in simple_recommendations:
                            filtered_tracks = [
                                t for t in simple_recommendations['tracks'] 
                                if t.get('album') and t['album'].get('images') and 
                                len(t['album']['images']) > 0 and
                                not t['album']['images'][0]['url'].endswith('dog.jpg')
                            ]
                            
                            # Add unique tracks
                            for track in filtered_tracks:
                                track_id = track.get('id')
                                if track_id and not any(t.get('id') == track_id for t in all_tracks):
                                    all_tracks.append(track)
                    
                    if all_tracks:
                        recommendations = {'tracks': all_tracks[:12]}
                        track_names = [t['name'] for t in all_tracks[:5]]
                        logger.debug(f"Got {len(all_tracks[:12])} simple recommendations: {track_names}")
                        
                        source = "spotify_simple"
                        logger.debug("Successfully got simple genre recommendations")
                    else:
                        raise Exception("No valid tracks after filtering")
                except Exception as e3:
                    logger.warning(f"Simple genre recommendations failed: {str(e3)}")
                    
                    # Method 4: Try with featured playlists as a more reliable option
                    try:
                        logger.debug("Trying to get tracks from featured playlists")
                        playlists = sp.featured_playlists(limit=8)
                        
                        if playlists and 'playlists' in playlists and playlists['playlists']['items']:
                            # Try multiple playlists to get more variety
                            all_tracks = []
                            
                            for playlist_item in playlists['playlists']['items'][:5]:  # Try up to 5 playlists
                                try:
                                    playlist_id = playlist_item['id']
                                    logger.debug(f"Checking featured playlist: {playlist_item['name']} (ID: {playlist_id})")
                                    
                                    tracks_response = sp.playlist_tracks(playlist_id, limit=10)
                                    
                                    if tracks_response and 'items' in tracks_response:
                                        playlist_tracks = [
                                            item['track'] for item in tracks_response['items'] 
                                            if item.get('track') and 
                                            item['track'].get('album') and 
                                            item['track']['album'].get('images') and 
                                            len(item['track']['album']['images']) > 0 and
                                            not item['track']['album']['images'][0]['url'].endswith('dog.jpg')
                                        ]
                                        
                                        # Add new unique tracks to our collection
                                        for track in playlist_tracks:
                                            track_id = track.get('id')
                                            if track_id and not any(t.get('id') == track_id for t in all_tracks):
                                                all_tracks.append(track)
                                        
                                        logger.debug(f"Found {len(playlist_tracks)} valid tracks in playlist {playlist_item['name']}")
                                        
                                        # If we have enough tracks, stop looking at more playlists
                                        if len(all_tracks) >= 15:
                                            break
                                except Exception as playlist_err:
                                    logger.warning(f"Error processing playlist {playlist_id}: {str(playlist_err)}")
                            
                            # Check if we found any tracks
                            if all_tracks:
                                # Randomize the order for variety
                                random.shuffle(all_tracks)
                                recommendations = {'tracks': all_tracks[:12]}
                                source = "spotify_featured_playlist"
                                logger.debug(f"Successfully got {len(all_tracks[:12])} tracks from featured playlists")
                            else:
                                raise Exception("No valid tracks found in any featured playlists")
                        else:
                            raise Exception("No featured playlists found")
                    except Exception as e4:
                        logger.warning(f"Featured playlist approach failed: {str(e4)}")
                        
                        # Method 5: Try with new releases
                        try:
                            logger.debug("Trying to get tracks from new releases")
                            new_releases = sp.new_releases(limit=15)
                            if new_releases and 'albums' in new_releases and new_releases['albums']['items']:
                                # Get more albums than before
                                albums = new_releases['albums']['items'][:8]
                                all_tracks = []
                                
                                for album in albums:
                                    try:
                                        album_id = album['id']
                                        album_name = album.get('name', 'Unknown Album')
                                        logger.debug(f"Checking album: {album_name} (ID: {album_id})")
                                        
                                        # Check if album has valid image
                                        has_valid_image = (
                                            album.get('images') and 
                                            len(album['images']) > 0 and
                                            'url' in album['images'][0] and
                                            not album['images'][0]['url'].endswith('dog.jpg')
                                        )
                                        
                                        if has_valid_image:
                                            album_tracks = sp.album_tracks(album_id, limit=5)
                                            if album_tracks and 'items' in album_tracks:
                                                # Format tracks to match recommendations format
                                                for track in album_tracks['items'][:2]:  # Get 2 tracks from each album
                                                    track_with_album = track.copy()
                                                    # Add album info if it's missing
                                                    if 'album' not in track_with_album:
                                                        track_with_album['album'] = album
                                                    
                                                    # Only add if not already in our list
                                                    track_id = track_with_album.get('id')
                                                    if track_id and not any(t.get('id') == track_id for t in all_tracks):
                                                        all_tracks.append(track_with_album)
                                                
                                                logger.debug(f"Added {len(album_tracks['items'][:2])} tracks from album {album_name}")
                                                
                                                # If we have enough tracks, stop processing more albums
                                                if len(all_tracks) >= 15:
                                                    break
                                    except Exception as album_err:
                                        logger.warning(f"Error getting album tracks: {str(album_err)}")
                                
                                if all_tracks:
                                    # Randomize the track order for variety
                                    random.shuffle(all_tracks)
                                    recommendations = {'tracks': all_tracks[:12]}
                                    source = "spotify_new_releases"
                                    logger.debug(f"Successfully got {len(all_tracks[:12])} tracks from new releases")
                                else:
                                    raise Exception("No tracks found in new releases")
                            else:
                                raise Exception("No new releases found")
                        except Exception as e5:
                            logger.warning(f"New releases approach failed: {str(e5)}")
                        
                            # Method 6: Use hardcoded backup tracks based on mood
                            if mood_category in BACKUP_TRACKS_BY_MOOD:
                                logger.warning(f"Using backup tracks for mood: {mood_category}")
                                recommendations = {'tracks': BACKUP_TRACKS_BY_MOOD[mood_category]}
                                source = f"fallback_{mood_category}"
                            else:
                                logger.warning("Using default backup tracks")
                                recommendations = {'tracks': BACKUP_TRACKS_BY_MOOD['default']}
                                source = "fallback_default"
        
        # Return the results
        if recommendations and 'tracks' in recommendations and recommendations['tracks']:
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': recommendations['tracks'],
                'source': source  # Include source in response
            })
        else:
            # This should never happen with our fallbacks, but just in case
            logger.error("No recommendations found after all attempts")
            if mood_category in BACKUP_TRACKS_BY_MOOD:
                backup_tracks = BACKUP_TRACKS_BY_MOOD[mood_category]
            else:
                backup_tracks = BACKUP_TRACKS_BY_MOOD['default']
                
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': backup_tracks,
                'source': 'fallback_last_resort'  # Include source in response
            })
            
    except Exception as e:
        logger.error(f"Error in analyze_mood: {str(e)}")
        traceback.print_exc()
        
        # Return backup tracks with the mood analysis
        try:
            if 'mood_category' in locals() and mood_category in BACKUP_TRACKS_BY_MOOD:
                backup_tracks = BACKUP_TRACKS_BY_MOOD[mood_category]
                source = f"error_fallback_{mood_category}"
            else:
                backup_tracks = BACKUP_TRACKS_BY_MOOD['default']
                source = "error_fallback_default"
                
            return jsonify({
                'mood_analysis': mood_analysis if 'mood_analysis' in locals() else "I analyzed your mood and found some music recommendations.",
                'recommendations': backup_tracks,
                'source': source  # Include source in response
            })
        except:
            # Ultimate fallback
            return jsonify({
                'mood_analysis': "I analyzed your mood and found some music recommendations.",
                'recommendations': BACKUP_TRACKS_BY_MOOD['default'],
                'source': 'ultimate_fallback'  # Include source in response
            })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)