# Moosic AI - Mood-Based Music Recommendations

A Flask web application that uses AI to analyze your mood and recommend music from Spotify.

## Features

- Spotify OAuth integration for user authentication
- AI-powered mood analysis using Google's Gemini API
- Personalized music recommendations based on mood
- Modern, responsive UI
- Mobile-friendly design

## Prerequisites

- Python 3.8 or higher
- Spotify Developer Account
- Google AI Studio Account (for Gemini API)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd moosic-ai
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Add a default avatar image:
   - Place a default avatar image named `default-avatar.png` in the `static` folder
   - This will be used for users without a Spotify profile picture

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. Visit the application in your web browser
2. Click "Connect with Spotify" to authenticate
3. Enter your mood in the text area
4. Click "Analyze Mood" to get personalized music recommendations
5. Click on any track to play it on Spotify

## Environment Variables

The following environment variables are required in the `.env` file:

- `SPOTIFY_CLIENT_ID`: Your Spotify API client ID
- `SPOTIFY_CLIENT_SECRET`: Your Spotify API client secret
- `SPOTIFY_REDIRECT_URI`: The callback URL (default: http://localhost:5000/callback)
- `GEMINI_API_KEY`: Your Google Gemini API key
- `FLASK_SECRET_KEY`: A secret key for Flask session management

## Security Notes

- Never commit your `.env` file or expose your API keys
- Keep your Flask secret key secure
- Use HTTPS in production

## License

MIT License 