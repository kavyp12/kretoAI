/**
 * YouTube Outlier Tool Frontend Logic
 * This script handles API calls, DOM manipulation, and user interactions.
 */
document.addEventListener('DOMContentLoaded', () => {

    // --- DOM Element References ---
    const searchForm = document.getElementById('searchForm');
    const searchBtn = document.getElementById('searchBtn');
    const searchBtnText = document.getElementById('searchBtnText');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsSection = document.getElementById('resultsSection');
    const resultsGrid = document.getElementById('resultsGrid');
    const resultsCount = document.getElementById('resultsCount');
    const infoPlaceholder = document.getElementById('info-placeholder');
    const popularSearchesContainer = document.getElementById('popularSearches');
    const exportBtn = document.getElementById('exportBtn');
    const toggleFiltersBtn = document.getElementById('toggleFiltersBtn');
    const filtersDiv = document.getElementById('filters');

    let currentResults = []; // Store current search results for export

    // --- Event Listeners ---

    /**
     * Handles the main search form submission.
     */
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        searchOutliers();
    });

    /**
     * Toggles the visibility of the advanced filters section.
     */
    toggleFiltersBtn.addEventListener('click', () => {
        filtersDiv.classList.toggle('hidden');
        const icon = toggleFiltersBtn.querySelector('i');
        icon.classList.toggle('fa-chevron-down');
        icon.classList.toggle('fa-chevron-up');
    });
    
    /**
     * Handles clicks on popular search tags.
     */
    popularSearchesContainer.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            document.getElementById('query').value = e.target.dataset.query;
            searchOutliers();
        }
    });

    /**
     * Handles the export to CSV functionality.
     */
    exportBtn.addEventListener('click', () => {
        if (currentResults.length > 0) {
            exportToCSV(currentResults);
        } else {
            showToast('No results to export.', 'error');
        }
    });

    // --- Core Functions ---

    /**
     * Fetches outlier data from the backend API and renders the results.
     */
    async function searchOutliers() {
        const query = document.getElementById('query').value.trim();
        if (!query) {
            showToast('Please enter a search topic.', 'error');
            return;
        }

        setLoadingState(true);
        hideInfoPlaceholder();
        resultsSection.classList.add('hidden');
        
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    filters: getFilters() // Pass filters as a nested object
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            }

            const result = await response.json();
            renderResults(result);

        } catch (error) {
            console.error('Search failed:', error);
            showInfoPlaceholder('error', `Search failed: ${error.message}`);
        } finally {
            setLoadingState(false);
        }
    }

    /**
     * Renders the search results on the page.
     * @param {object} data - The API response data.
     */
    function renderResults(data) {
        currentResults = data.outliers || [];
        resultsGrid.innerHTML = '';

        if (currentResults.length === 0) {
            showInfoPlaceholder('no-results', `No outliers found for "${data.query}". Try a different search or loosen your filters.`);
            return;
        }
        
        resultsSection.classList.remove('hidden');
        resultsCount.innerHTML = `Found <span class="text-blue-600 font-bold">${data.total_results}</span> outlier videos for "<span class="text-blue-600 font-bold">${data.query}</span>"`;
        
        const fragment = document.createDocumentFragment();
        currentResults.forEach(video => {
            fragment.appendChild(createVideoCard(video));
        });
        resultsGrid.appendChild(fragment);
    }
    
    /**
     * Creates an HTML element for a single video card with advanced data.
     * @param {object} video - The video data object.
     * @returns {HTMLElement} - The video card element.
     */
    function createVideoCard(video) {
        const card = document.createElement('div');
        card.className = 'video-card';

        const tierColor = {
            "Mega Viral": "bg-red-500",
            "Super Viral": "bg-orange-500",
            "Highly Viral": "bg-amber-500",
            "Viral": "bg-yellow-500",
            "Above Average": "bg-lime-500",
            "Average": "bg-gray-400"
        };
        const tierClass = tierColor[video.performance_tier] || 'bg-gray-400';

        card.innerHTML = `
            <div class="relative">
                <a href="${video.url}" target="_blank" rel="noopener noreferrer">
                    <img src="https://i.ytimg.com/vi/${video.video_id}/hqdefault.jpg" alt="Thumbnail for ${video.title}" class="w-full h-48 object-cover" loading="lazy" onerror="this.src='https://placehold.co/480x360/e2e8f0/94a3b8?text=No+Thumbnail'">
                </a>
                <div class="absolute top-2 left-2 text-white text-xs font-bold px-2 py-1 rounded-full ${tierClass}">
                    ${video.performance_tier}
                </div>
                <div class="absolute top-2 right-2 text-white text-lg font-bold px-3 py-1 rounded-full bg-slate-800 bg-opacity-70 backdrop-blur-sm">
                    ${video.multiplier}x
                </div>
            </div>
            <div class="p-4 flex flex-col flex-grow">
                <h3 class="text-md font-bold text-gray-800 mb-2 line-clamp-2" title="${video.title}">
                    <a href="${video.url}" target="_blank" rel="noopener noreferrer">#${video.rank || ''} ${video.title}</a>
                </h3>
                <p class="text-sm text-gray-600 mb-4 line-clamp-1" title="${video.channel_title}">
                    <i class="fas fa-user-circle mr-1 text-gray-400"></i>${video.channel_title}
                </p>
                <div class="mt-auto space-y-2 text-sm">
                    <div class="flex justify-between items-center"><span class="text-gray-500"><i class="fas fa-eye w-4"></i> Video Views</span> <span class="font-semibold">${video.views_formatted}</span></div>
                    <div class="flex justify-between items-center"><span class="text-gray-500"><i class="fas fa-chart-pie w-4"></i> Channel Avg</span> <span class="font-semibold">${video.channel_avg_views_formatted}</span></div>
                    <div class="flex justify-between items-center"><span class="text-gray-500"><i class="fas fa-thumbs-up w-4"></i> Likes</span> <span class="font-semibold">${video.likes_formatted}</span></div>
                    <div class="flex justify-between items-center"><span class="text-gray-500"><i class="fas fa-calendar-day w-4"></i> Age</span> <span class="font-semibold">${video.video_age_days} days</span></div>
                    <div class="flex justify-between items-center"><span class="text-gray-500"><i class="fas fa-fire w-4"></i> Viral Score</span> <span class="font-semibold">${video.viral_score}</span></div>
                </div>
            </div>
        `;
        return card;
    }
    
    /**
     * Fetches and displays popular searches.
     */
    async function loadPopularSearches() {
        try {
            const response = await fetch('/api/stats');
            const result = await response.json();
            if (result.success && result.stats.popular_searches) {
                popularSearchesContainer.innerHTML = result.stats.popular_searches
                    .map(s => `<button class="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm hover:bg-blue-200 transition-colors" data-query="${s._id}">${s._id}</button>`)
                    .join('');
            }
        } catch (error) {
            console.error('Error loading popular searches:', error);
            popularSearchesContainer.innerHTML = '<p class="text-sm text-gray-500">Could not load popular searches.</p>';
        }
    }

    // --- UI & Utility Functions ---

    /**
     * Gathers and formats filter values from the form.
     * @returns {object} - An object containing the filter values.
     */
    function getFilters() {
        const filters = {};
        const fields = [
            'min_multiplier', 'max_multiplier', 'min_views', 'max_views',
            'min_duration_minutes', 'max_duration_minutes', 'min_subscribers', 'max_subscribers',
            'min_viral_score', 'max_age_days'
        ];
        
        fields.forEach(id => {
            const element = document.getElementById(id);
            if (element && element.value) {
                // Use parseFloat for potential decimals, parseInt for others
                const value = id.includes('multiplier') ? parseFloat(element.value) : parseInt(element.value, 10);
                if (!isNaN(value)) {
                    filters[id] = value;
                }
            }
        });
        return filters;
    }

    /**
     * Toggles the UI's loading state.
     * @param {boolean} isLoading - True to show loading, false to hide.
     */
    function setLoadingState(isLoading) {
        searchBtn.disabled = isLoading;
        searchBtnText.classList.toggle('hidden', isLoading);
        loadingSpinner.classList.toggle('hidden', !isLoading);
    }

    /**
     * Displays a toast notification.
     * @param {string} message - The message to display.
     * @param {string} type - 'success' or 'error'.
     */
    function showToast(message, type = 'error') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toast-message');
        
        toastMessage.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    /**
     * Shows a placeholder message for errors or no results.
     * @param {string} type - 'error' or 'no-results'.
     * @param {string} message - The message to display.
     */
    function showInfoPlaceholder(type, message) {
        const icon = type === 'error' 
            ? '<i class="fas fa-exclamation-triangle text-red-400 text-6xl mb-4"></i>'
            : '<i class="fas fa-search text-gray-400 text-6xl mb-4"></i>';
            
        infoPlaceholder.innerHTML = `
            ${icon}
            <h3 class="text-xl font-semibold text-gray-600 mb-2">${type === 'error' ? 'An Error Occurred' : 'No Results'}</h3>
            <p class="text-gray-500">${message}</p>
        `;
        infoPlaceholder.classList.remove('hidden');
    }

    function hideInfoPlaceholder() {
        infoPlaceholder.classList.add('hidden');
    }

    /**
     * Converts an array of objects to a CSV string and triggers a download.
     * @param {Array<object>} data - The data to convert.
     */
    function exportToCSV(data) {
        const headers = [
            'Rank', 'Title', 'Channel', 'URL', 'Multiplier', 'Performance Tier', 'Composite Score', 'Viral Score',
            'Views', 'Channel Avg Views', 'Likes', 'Comments', 'Duration (s)', 'Video Age (Days)', 'Published At'
        ];
        
        const rows = data.map(video => [
            video.rank,
            `"${video.title.replace(/"/g, '""')}"`,
            `"${video.channel_title.replace(/"/g, '""')}"`,
            video.url,
            video.multiplier,
            video.performance_tier,
            video.composite_score,
            video.viral_score,
            video.views,
            video.channel_avg_views,
            video.likes,
            video.comments,
            video.duration_seconds,
            video.video_age_days,
            video.published_at
        ]);

        const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `youtube_outliers_${new Date().toISOString().slice(0,10)}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    // --- Initial Load ---
    loadPopularSearches();
});