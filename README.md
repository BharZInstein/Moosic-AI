# Moosik AI - Mood-Based Music Recommendations

A Flask web application that analyzes your mood from text descriptions and recommends music from Spotify based on that mood.

## Features

- Text-based mood analysis
- Integration with Spotify API for personalized music recommendations
- Support for multiple moods: happy, sad, relaxed, energetic, focused, angry, nostalgic, etc.
- Multiple fallback mechanisms to ensure you always get good recommendations
- Filters out low-quality or problematic album artwork

## Setup Instructions

### Prerequisites

- Python 3.7+
- pip (Python package manager)
- Spotify Developer Account (for API credentials)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/moosik-ai.git
cd moosik-ai
```

### Step 2: Create and Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your own credentials:
   - Get your Spotify credentials from the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Create a new application in the dashboard
   - Add `http://localhost:5000/callback` as a Redirect URI in your Spotify app settings
   - Copy your Client ID and Client Secret to the `.env` file
   - Generate a random string for the Flask secret key

### Step 3: Set Up Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# For Windows:
venv\Scripts\activate
# For macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python app.py
```

The application will start at http://localhost:5000

## Usage

1. Open the application in your web browser
2. Log in with your Spotify account
3. Enter a text description of your current mood (e.g., "I'm feeling happy today" or "I need to focus on my work")
4. The app will analyze your mood and recommend suitable music from Spotify
5. Click on any song to listen on Spotify

## How It Works

1. The app analyzes your text input to determine your mood
2. Based on the detected mood, it selects appropriate audio features and genres
3. It uses the Spotify API to find music that matches those parameters
4. Multiple recommendation strategies are tried to ensure you get good results
5. Results are filtered to ensure quality and uniqueness

## Troubleshooting

- If you receive fallback tracks consistently, check your Spotify API credentials
- Make sure your Spotify account is active and properly connected
- Clear your browser cookies if you experience authentication issues
- Check the app logs for detailed error information

## License

[MIT License](LICENSE)

## Acknowledgments

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
- [Flask](https://flask.palletsprojects.com/)
- [Spotipy](https://spotipy.readthedocs.io/) 