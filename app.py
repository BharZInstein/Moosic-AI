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

# Define a simple mood analyzer function
def analyze_mood_text(text):
    """Simple rule-based mood analyzer as a fallback for the Gemini API"""
    text = text.lower()
    
    # Define mood keywords and their corresponding analysis and genres
    # Map our moods to valid Spotify genres
    mood_map = {
        'happy': {
            'analysis': 'You seem happy and upbeat! Your mood is positive and energetic.',
            'genre': 'happy'
        },
        'sad': {
            'analysis': 'You seem to be feeling down or melancholic. Music can help lift your spirits.',
            'genre': 'sad'
        },
        'angry': {
            'analysis': 'Your text suggests feelings of frustration or anger. Some energizing music might help.',
            'genre': 'rock'
        },
        'tired': {
            'analysis': 'You sound tired or fatigued. Some relaxing music could be just what you need.',
            'genre': 'chill'
        },
        'excited': {
            'analysis': 'You seem very excited and enthusiastic! Some upbeat music would match your energy.',
            'genre': 'dance'
        },
        'relaxed': {
            'analysis': 'You appear to be in a calm, relaxed state. Some smooth music would complement this well.',
            'genre': 'ambient'
        },
        'stressed': {
            'analysis': 'You seem to be experiencing stress. Some calming music might help you unwind.',
            'genre': 'classical'
        },
        'bored': {
            'analysis': 'You sound a bit bored or understimulated. Some engaging music could help.',
            'genre': 'pop'
        },
        'nostalgic': {
            'analysis': 'Your words have a nostalgic quality. Music that reminds you of good times might resonate.',
            'genre': 'rock-n-roll'
        },
        'focused': {
            'analysis': 'You seem to be in a focused state. Some concentration-enhancing music could help maintain this.',
            'genre': 'study'
        },
        'sleepy': {
            'analysis': 'You sound sleepy or drowsy. Some gentle music could help you relax further.',
            'genre': 'sleep'
        },
        'energetic': {
            'analysis': 'Your text suggests high energy levels. Some upbeat music would match this well.',
            'genre': 'work-out'
        },
        'calm': {
            'analysis': 'You seem calm and collected. Some gentle music would complement this mood.',
            'genre': 'chill'
        },
        'anxious': {
            'analysis': 'Your text suggests some anxiety or worry. Some calming music might help you relax.',
            'genre': 'ambient'
        },
        'love': {
            'analysis': 'Your words suggest feelings of love or romance. Some heartfelt music would match this mood.',
            'genre': 'romance'
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
            safe_genres = ["pop", "rock", "indie", "chill"]
            return {
                'analysis': 'I analyzed your text and will recommend some popular music that might match your current state.',
                'genre': random.choice(safe_genres)
            }
    
    # Use the first matched mood
    chosen_mood = matched_moods[0]
    return mood_map[chosen_mood]

# Function to get a fresh access token if needed
def get_spotify_client():
    """Get a fresh Spotify client with valid access token"""
    if 'token_info' not in session:
        return None
    
    token_info = session['token_info']
    
    # Check if token is expired and refresh if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    
    return Spotify(auth=token_info['access_token'])

# Hardcoded backup tracks (as a last resort)
BACKUP_TRACKS = [
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
        
        logger.debug(f"Mood analysis result: {mood_analysis}")
        logger.debug(f"Selected genre: {genre}")
        
        # Get a fresh Spotify client
        sp = get_spotify_client()
        if not sp:
            return jsonify({'error': 'Spotify authentication expired'}), 401
        
        # Try multiple methods to get recommendations, with increasing fallbacks
        recommendations = None
        
        # Method 1: Try genre-based recommendations
        try:
            logger.debug("Trying genre-based recommendations")
            
            # Ensure we're using a valid genre
            if genre not in VALID_SPOTIFY_GENRES:
                logger.warning(f"Genre {genre} not found in valid Spotify genres, using pop instead")
                genre = "pop"
            
            # Debug: Get and log available genres
            try:
                available_genres = sp.recommendation_genre_seeds()
                logger.debug(f"Available Spotify genres: {available_genres}")
            except Exception as genre_err:
                logger.warning(f"Failed to get genre seeds: {genre_err}")
            
            # Try with genre recommendation
            recommendations = sp.recommendations(seed_genres=[genre], limit=5)
            logger.debug("Successfully got genre-based recommendations")
        except Exception as e:
            logger.warning(f"Genre-based recommendations failed: {str(e)}")
            traceback.print_exc()
            
            # Method 2: Try with artist seeding from newly released tracks
            try:
                logger.debug("Trying artist-based recommendations from new releases")
                new_releases = sp.new_releases(limit=2)
                if new_releases and 'albums' in new_releases and new_releases['albums']['items']:
                    # Get artist IDs from new releases
                    artist_ids = [album['artists'][0]['id'] for album in new_releases['albums']['items']]
                    recommendations = sp.recommendations(seed_artists=artist_ids[:2], limit=5)
                    logger.debug("Successfully got artist-based recommendations")
                else:
                    raise Exception("No new releases found")
            except Exception as e2:
                logger.warning(f"Artist-based recommendations failed: {str(e2)}")
                
                # Method 3: Try with featured playlists
                try:
                    logger.debug("Trying to get tracks from featured playlists")
                    playlists = sp.featured_playlists(limit=1)
                    if playlists and 'playlists' in playlists and playlists['playlists']['items']:
                        playlist_id = playlists['playlists']['items'][0]['id']
                        tracks_response = sp.playlist_tracks(playlist_id, limit=5)
                        
                        if tracks_response and 'items' in tracks_response:
                            tracks = [item['track'] for item in tracks_response['items'] if item.get('track')]
                            if tracks:
                                recommendations = {'tracks': tracks}
                                logger.debug("Successfully got tracks from featured playlist")
                            else:
                                raise Exception("No tracks found in playlist")
                        else:
                            raise Exception("Invalid playlist tracks response")
                    else:
                        raise Exception("No featured playlists found")
                except Exception as e3:
                    logger.warning(f"Featured playlist approach failed: {str(e3)}")
                    
                    # Method 4: Use hardcoded backup tracks as last resort
                    logger.warning("Using hardcoded backup tracks as last resort")
                    recommendations = {'tracks': BACKUP_TRACKS}
        
        # Return the results
        if recommendations and 'tracks' in recommendations and recommendations['tracks']:
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': recommendations['tracks']
            })
        else:
            # This should never happen with our fallbacks, but just in case
            logger.error("No recommendations found after all attempts")
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': BACKUP_TRACKS
            })
            
    except Exception as e:
        logger.error(f"Error in analyze_mood: {str(e)}")
        traceback.print_exc()
        
        # Return backup tracks with the mood analysis
        try:
            return jsonify({
                'mood_analysis': mood_analysis if 'mood_analysis' in locals() else "I analyzed your mood and found some music recommendations.",
                'recommendations': BACKUP_TRACKS
            })
        except:
            # Ultimate fallback
            return jsonify({
                'mood_analysis': "I analyzed your mood and found some music recommendations.",
                'recommendations': BACKUP_TRACKS
            })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)