document.addEventListener('DOMContentLoaded', () => {
    const moodText = document.getElementById('moodText');
    const analyzeButton = document.getElementById('analyzeMood');
    const resultsSection = document.getElementById('resultsSection');
    const moodAnalysis = document.getElementById('moodAnalysis');
    const recommendationsList = document.getElementById('recommendationsList');
    const errorMessage = document.getElementById('errorMessage');
    const defaultImage = document.body.dataset.defaultImage || '/static/default-avatar.png';
    const moodChips = document.querySelectorAll('.chips span');
    const defaultButtonText = analyzeButton ? analyzeButton.textContent : 'Analyze Mood';

    const setLoadingState = (isLoading) => {
        analyzeButton.disabled = isLoading;
        analyzeButton.textContent = isLoading ? 'Analyzing...' : defaultButtonText;
        moodText.classList.toggle('loading', isLoading);
    };

    const clearResults = () => {
        resultsSection.style.display = 'none';
        moodAnalysis.textContent = '';
        recommendationsList.innerHTML = '';
    };

    const hideError = () => {
        errorMessage.style.display = 'none';
        errorMessage.innerHTML = '';
    };

    const showError = (message) => {
        errorMessage.innerHTML = `
            <h3>Error</h3>
            <p>${message}</p>
            <p>Please try again or describe your mood differently.</p>
        `;
        errorMessage.style.display = 'block';
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    };

    analyzeButton.addEventListener('click', async () => {
        const text = moodText.value.trim();
        if (!text) {
            alert('Please enter some text about your mood.');
            return;
        }

        setLoadingState(true);
        clearResults();
        hideError();

        try {
            const response = await fetch('/analyze_mood', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze mood');
            }

            moodAnalysis.textContent = data.mood_analysis || 'No mood analysis available.';

            const sourceInfo = data.source
                ? `<div class="source-info">Source: ${formatSourceInfo(data.source)}</div>`
                : '';

            if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
                const cards = data.recommendations
                    .map((track) => buildTrackCard(track))
                    .join('');
                recommendationsList.innerHTML = sourceInfo + cards;
            } else {
                recommendationsList.innerHTML =
                    sourceInfo + '<p>No recommendations found. Try describing your mood differently.</p>';
            }

            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'Failed to analyze mood.');
        } finally {
            setLoadingState(false);
        }
    });

    moodChips.forEach((chip) => {
        chip.addEventListener('click', () => {
            moodText.value = chip.textContent;
            moodText.focus();
        });
    });

    const buildTrackCard = (track) => {
        const imageUrl =
            track?.album?.images && track.album.images.length > 0
                ? track.album.images[0].url
                : defaultImage;
        const artistNames = Array.isArray(track?.artists)
            ? track.artists.map((artist) => artist.name).join(', ')
            : 'Unknown Artist';
        const spotifyUrl = track?.external_urls?.spotify || '#';

        return `
            <div class="track-card">
                <img src="${imageUrl}" alt="${track?.name || 'Track artwork'}">
                <h4>${track?.name || 'Unknown Track'}</h4>
                <p>${artistNames}</p>
                <a href="${spotifyUrl}" target="_blank" rel="noopener" class="cta-button">Play on Spotify</a>
            </div>
        `;
    };

    const formatSourceInfo = (source) => {
        if (!source) {
            return 'Unknown source';
        }

        if (source.startsWith('spotify_advanced')) {
            return 'Spotify API with advanced mood parameters';
        }
        if (source.startsWith('spotify_simple')) {
            return 'Spotify API with basic genre recommendations';
        }
        if (source.startsWith('spotify_new_releases')) {
            return 'Spotify API based on new releases';
        }
        if (source.startsWith('spotify_featured_playlist')) {
            return 'Spotify API featured playlist';
        }
        if (source.startsWith('spotify_user_top_tracks')) {
            return 'Spotify API using your top tracks';
        }
        if (source.startsWith('fallback_')) {
            const mood = source.replace('fallback_', '');
            return `Fallback tracks for ${mood} mood`;
        }
        if (source.includes('fallback')) {
            return 'Fallback tracks';
        }
        return source;
    };
});