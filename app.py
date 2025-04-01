from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import json
import logging
import re
import random

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Spotify OAuth setup
sp_oauth = SpotifyOAuth(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
    redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
    scope='user-library-read playlist-read-private user-read-private user-read-email'
)

# List of valid Spotify genres we can use for recommendations
# These are guaranteed to work with the API
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    sp = Spotify(auth=session['token_info']['access_token'])
    user_info = sp.current_user()
    return render_template('dashboard.html', user=user_info)

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
        
        # Get Spotify recommendations based on mood
        sp = Spotify(auth=session['token_info']['access_token'])
        
        try:
            # Ensure we're using a valid genre
            if genre not in VALID_SPOTIFY_GENRES:
                logger.warning(f"Genre {genre} not found in valid Spotify genres, using pop instead")
                genre = "pop"
                
            # Get available genres from Spotify (for debugging)
            available_genres = sp.recommendation_genre_seeds()
            logger.debug(f"Available Spotify genres: {available_genres}")
            
            # Get personalized recommendations using the valid genre
            recommendations = sp.recommendations(seed_genres=[genre], limit=5)
            
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': recommendations['tracks']
            })
        except Exception as e:
            logger.error(f"Error getting Spotify recommendations: {str(e)}")
            
            # Try a different approach if recommendations fail
            try:
                # Get user's top tracks and use their artists as seeds instead
                top_tracks = sp.current_user_top_tracks(limit=5)
                if top_tracks and top_tracks.get('items'):
                    artist_ids = [track['artists'][0]['id'] for track in top_tracks['items'][:2]]
                    recommendations = sp.recommendations(seed_artists=artist_ids, limit=5)
                    
                    return jsonify({
                        'mood_analysis': mood_analysis,
                        'recommendations': recommendations['tracks']
                    })
                else:
                    # Last resort: get featured playlists and return tracks from there
                    playlists = sp.featured_playlists(limit=1)
                    if playlists and playlists.get('playlists') and playlists['playlists'].get('items'):
                        playlist_id = playlists['playlists']['items'][0]['id']
                        tracks = sp.playlist_tracks(playlist_id, limit=5)
                        return jsonify({
                            'mood_analysis': mood_analysis,
                            'recommendations': [item['track'] for item in tracks['items']]
                        })
            except Exception as backup_error:
                logger.error(f"Backup recommendation method failed: {str(backup_error)}")
            
            return jsonify({
                'mood_analysis': mood_analysis,
                'error': f'Could not fetch music recommendations. Please try again later.'
            }), 500
        
    except Exception as e:
        logger.error(f"Error in analyze_mood: {str(e)}")
        return jsonify({'error': f'Failed to analyze mood: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)