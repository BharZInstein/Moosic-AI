document.addEventListener('DOMContentLoaded', () => {
    const moodText = document.getElementById('moodText');
    const analyzeButton = document.getElementById('analyzeMood');
    const resultsSection = document.getElementById('resultsSection');
    const moodAnalysis = document.getElementById('moodAnalysis');
    const recommendationsList = document.getElementById('recommendationsList');

    // Add loading state styles
    const style = document.createElement('style');
    style.textContent = `
        .loading {
            opacity: 0.7;
            pointer-events: none;
        }
        .error-message {
            color: #ff7675;
            background: #fff5f5;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
        .track-card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            padding: 1rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .track-card img {
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }
        .track-card h4 {
            margin: 0.5rem 0;
            font-size: 1.1rem;
        }
        .track-card p {
            margin: 0.25rem 0 1rem;
            color: #666;
        }
        .cta-button {
            background: #1DB954;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 0.5rem 1.5rem;
            font-weight: bold;
            text-decoration: none;
            transition: background 0.3s;
        }
        .cta-button:hover {
            background: #179443;
        }
        #recommendationsList {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .source-info {
            background: #e2f0ff;
            color: #0056b3;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.85rem;
            margin: 0.5rem 0;
        }
    `;
    document.head.appendChild(style);

    analyzeButton.addEventListener('click', async () => {
        const text = moodText.value.trim();
        if (!text) {
            alert('Please enter some text about your mood.');
            return;
        }

        try {
            // Add loading state
            analyzeButton.disabled = true;
            analyzeButton.textContent = 'Analyzing...';
            moodText.classList.add('loading');
            
            // Clear previous results
            resultsSection.style.display = 'none';
            moodAnalysis.textContent = '';
            recommendationsList.innerHTML = '';

            const response = await fetch('/analyze_mood', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to analyze mood');
            }
            
            // Display mood analysis
            moodAnalysis.textContent = data.mood_analysis;
            
            // Display source information if available
            let sourceHTML = '';
            if (data.source) {
                sourceHTML = `<div class="source-info">Source: ${formatSourceInfo(data.source)}</div>`;
            }
            
            // Display recommendations
            if (data.recommendations && data.recommendations.length > 0) {
                recommendationsList.innerHTML = sourceHTML + data.recommendations
                    .map(track => `
                        <div class="track-card">
                            <img src="${track.album.images[0].url}" alt="${track.name}">
                            <h4>${track.name}</h4>
                            <p>${track.artists.map(artist => artist.name).join(', ')}</p>
                            <a href="${track.external_urls.spotify}" target="_blank" class="cta-button">Play on Spotify</a>
                        </div>
                    `)
                    .join('');
            } else {
                recommendationsList.innerHTML = sourceHTML + '<p>No recommendations found. Try describing your mood differently.</p>';
            }

            // Show results section
            resultsSection.style.display = 'block';
            
            // Scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error('Error:', error);
            // Display error message in the UI
            resultsSection.style.display = 'block';
            resultsSection.innerHTML = `
                <div class="error-message">
                    <h3>Error</h3>
                    <p>${error.message}</p>
                    <p>Please try again or describe your mood differently.</p>
                </div>
            `;
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        } finally {
            // Remove loading state
            analyzeButton.disabled = false;
            analyzeButton.textContent = 'Analyze Mood';
            moodText.classList.remove('loading');
        }
    });
    
    // Format source info into a more user-friendly message
    function formatSourceInfo(source) {
        if (source.startsWith('spotify_advanced')) {
            return 'Spotify API with advanced mood parameters';
        } else if (source.startsWith('spotify_simple')) {
            return 'Spotify API with basic genre recommendations';
        } else if (source.startsWith('spotify_new_releases')) {
            return 'Spotify API based on new releases';
        } else if (source.startsWith('spotify_featured_playlist')) {
            return 'Spotify API featured playlist';
        } else if (source.startsWith('fallback_')) {
            const mood = source.replace('fallback_', '');
            return `Fallback tracks for ${mood} mood`;
        } else if (source.includes('fallback')) {
            return 'Fallback tracks';
        } else {
            return source;
        }
    }
});