from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import json
import logging
import re

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

# Define a simple fallback mood analyzer function
def analyze_mood_text(text):
    """Simple rule-based mood analyzer as a fallback for the Gemini API"""
    text = text.lower()
    
    # Define mood keywords and their corresponding analysis and genres
    mood_map = {
        'happy': {
            'analysis': 'You seem happy and upbeat! Your mood is positive and energetic.',
            'genre': 'pop'
        },
        'sad': {
            'analysis': 'You seem to be feeling down or melancholic. Music can help lift your spirits.',
            'genre': 'indie'
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
            'genre': 'classic'
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
            'genre': 'workout'
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
            # Default if no mood is detected
            return {
                'analysis': 'I analyzed your text and will recommend some popular music that might match your current state.',
                'genre': 'pop'
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
        # Use our fallback mood analyzer instead of Gemini
        logger.debug(f"Analyzing mood text: {text}")
        mood_result = analyze_mood_text(text)
        mood_analysis = mood_result['analysis']
        genre = mood_result['genre']
        
        logger.debug(f"Mood analysis result: {mood_analysis}")
        logger.debug(f"Selected genre: {genre}")
        
        # Get Spotify recommendations based on mood
        sp = Spotify(auth=session['token_info']['access_token'])
        
        try:
            # Get personalized recommendations
            recommendations = sp.recommendations(seed_genres=[genre], limit=5)
            
            return jsonify({
                'mood_analysis': mood_analysis,
                'recommendations': recommendations['tracks']
            })
        except Exception as e:
            logger.error(f"Error getting Spotify recommendations: {str(e)}")
            return jsonify({
                'mood_analysis': mood_analysis,
                'error': f'Could not fetch music recommendations: {str(e)}'
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