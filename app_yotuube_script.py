from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import re
import json
import time
from datetime import datetime, timedelta
import requests
from pymongo import MongoClient
import google.generativeai as genai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from functools import wraps
from collections import Counter
import statistics

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'

# API Keys and Configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MONGO_URI = os.getenv('MONGO_URI')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME')

# YouTube API setup
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Gemini AI setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client[MONGODB_DB_NAME]
channels_collection = db.channels
videos_collection = db.videos
scripts_collection = db.scripts

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting decorator
def rate_limit(max_calls=10, period=60):
    def decorator(func):
        calls = []
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [call for call in calls if call > now - period]
            if len(calls) >= max_calls:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

class YouTubeAnalyzer:
    def __init__(self):
        self.cache_duration = int(os.getenv('CACHE_DURATION_SECONDS', 3600))
        self.max_videos = int(os.getenv('MAX_VIDEOS_PER_REQUEST', 50))
    
    def extract_channel_id(self, channel_input):
        """Extract channel ID from various YouTube URL formats or handle @username"""
        channel_input = channel_input.strip()
        
        # Handle @username format
        if channel_input.startswith('@'):
            try:
                search_response = youtube.search().list(
                    part='snippet',
                    q=channel_input,
                    type='channel',
                    maxResults=1
                ).execute()
                
                if search_response['items']:
                    return search_response['items'][0]['snippet']['channelId']
            except HttpError as e:
                logger.error(f"Error searching for channel: {e}")
                return None
        
        # Handle direct channel ID
        if len(channel_input) == 24 and channel_input.startswith('UC'):
            return channel_input
        
        # Handle YouTube URLs
        patterns = [
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_input)
            if match:
                username = match.group(1)
                if pattern.endswith('([a-zA-Z0-9_-]+)') and not channel_input.startswith('UC'):
                    # Convert username to channel ID
                    try:
                        search_response = youtube.search().list(
                            part='snippet',
                            q=username,
                            type='channel',
                            maxResults=1
                        ).execute()
                        
                        if search_response['items']:
                            return search_response['items'][0]['snippet']['channelId']
                    except HttpError as e:
                        logger.error(f"Error converting username to channel ID: {e}")
                        return None
                else:
                    return username
        
        return None
    
    def get_channel_info(self, channel_id):
        """Get basic channel information"""
        try:
            # Check cache
            cached_channel = channels_collection.find_one({
                'channel_id': channel_id,
                'cached_at': {'$gt': datetime.utcnow() - timedelta(seconds=self.cache_duration)}
            })
            
            if cached_channel:
                return cached_channel
            
            # Fetch from YouTube API
            response = youtube.channels().list(
                part='snippet,statistics,brandingSettings',
                id=channel_id
            ).execute()
            
            if not response['items']:
                return None
            
            channel_data = response['items'][0]
            
            channel_info = {
                'channel_id': channel_id,
                'title': channel_data['snippet']['title'],
                'description': channel_data['snippet']['description'],
                'subscriber_count': int(channel_data['statistics'].get('subscriberCount', 0)),
                'video_count': int(channel_data['statistics'].get('videoCount', 0)),
                'view_count': int(channel_data['statistics'].get('viewCount', 0)),
                'thumbnail': channel_data['snippet']['thumbnails']['high']['url'],
                'country': channel_data['snippet'].get('country', ''),
                'cached_at': datetime.utcnow()
            }
            
            # Save to cache
            channels_collection.replace_one(
                {'channel_id': channel_id},
                channel_info,
                upsert=True
            )
            
            return channel_info
            
        except HttpError as e:
            logger.error(f"Error fetching channel info: {e}")
            return None
    
    def get_recent_videos(self, channel_id, max_results=None):
        """Get recent videos from a channel"""
        if max_results is None:
            max_results = self.max_videos
        
        try:
            # Check cache
            cached_videos = list(videos_collection.find({
                'channel_id': channel_id,
                'cached_at': {'$gt': datetime.utcnow() - timedelta(seconds=self.cache_duration)}
            }).sort('published_at', -1).limit(max_results))
            
            if cached_videos:
                return cached_videos
            
            # Fetch from YouTube API
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                search_response = youtube.search().list(
                    part='snippet',
                    channelId=channel_id,
                    type='video',
                    order='date',
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token
                ).execute()
                
                video_ids = [item['id']['videoId'] for item in search_response['items']]
                
                # Get detailed video information
                videos_response = youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(video_ids)
                ).execute()
                
                for video in videos_response['items']:
                    video_data = {
                        'video_id': video['id'],
                        'channel_id': channel_id,
                        'title': video['snippet']['title'],
                        'description': video['snippet']['description'],
                        'published_at': datetime.fromisoformat(video['snippet']['publishedAt'].replace('Z', '+00:00')),
                        'view_count': int(video['statistics'].get('viewCount', 0)),
                        'like_count': int(video['statistics'].get('likeCount', 0)),
                        'comment_count': int(video['statistics'].get('commentCount', 0)),
                        'duration': video['contentDetails']['duration'],
                        'tags': video['snippet'].get('tags', []),
                        'thumbnail': video['snippet']['thumbnails']['high']['url'],
                        'cached_at': datetime.utcnow()
                    }
                    videos.append(video_data)
                
                next_page_token = search_response.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Save to cache
            if videos:
                videos_collection.delete_many({'channel_id': channel_id})
                videos_collection.insert_many(videos)
            
            return videos[:max_results]
            
        except HttpError as e:
            logger.error(f"Error fetching videos: {e}")
            return []
    
    def analyze_channel_style(self, channel_info, videos):
        """Analyze channel's content style and patterns"""
        if not videos:
            return {}
        
        # Analyze titles
        titles = [video['title'] for video in videos]
        title_lengths = [len(title) for title in titles]
        
        # Analyze descriptions
        descriptions = [video['description'] for video in videos]
        description_lengths = [len(desc) for desc in descriptions if desc]
        
        # Analyze tags
        all_tags = []
        for video in videos:
            all_tags.extend(video.get('tags', []))
        
        common_tags = Counter(all_tags).most_common(20)
        
        # Analyze performance metrics
        view_counts = [video['view_count'] for video in videos]
        like_counts = [video['like_count'] for video in videos]
        
        # Extract common keywords from titles
        title_words = []
        for title in titles:
            words = re.findall(r'\b\w+\b', title.lower())
            title_words.extend(words)
        
        common_title_words = Counter(title_words).most_common(30)
        
        analysis = {
            'total_videos_analyzed': len(videos),
            'average_title_length': statistics.mean(title_lengths) if title_lengths else 0,
            'average_description_length': statistics.mean(description_lengths) if description_lengths else 0,
            'common_tags': common_tags,
            'common_title_words': common_title_words,
            'average_views': statistics.mean(view_counts) if view_counts else 0,
            'average_likes': statistics.mean(like_counts) if like_counts else 0,
            'recent_titles': titles[:10],  # Most recent 10 titles
            'channel_theme': self._extract_channel_theme(channel_info, videos),
            'content_style': self._analyze_content_style(descriptions[:10])  # Recent descriptions
        }
        
        return analysis
    
    def _extract_channel_theme(self, channel_info, videos):
        """Extract the main theme/niche of the channel"""
        # Combine channel description and video titles for theme extraction
        text_for_analysis = channel_info.get('description', '') + ' '
        text_for_analysis += ' '.join([video['title'] for video in videos[:20]])
        
        # Simple keyword-based theme detection
        themes = {
            'tech': ['technology', 'tech', 'programming', 'coding', 'software', 'app', 'gadget', 'review'],
            'gaming': ['game', 'gaming', 'gameplay', 'play', 'player', 'level', 'boss', 'stream'],
            'education': ['learn', 'tutorial', 'how to', 'guide', 'lesson', 'course', 'study', 'explain'],
            'lifestyle': ['life', 'daily', 'routine', 'vlog', 'personal', 'lifestyle', 'day in my life'],
            'entertainment': ['funny', 'comedy', 'entertainment', 'fun', 'laugh', 'joke', 'story'],
            'business': ['business', 'entrepreneur', 'startup', 'money', 'finance', 'marketing', 'sales'],
            'fitness': ['workout', 'fitness', 'gym', 'exercise', 'health', 'training', 'muscle'],
            'cooking': ['recipe', 'cooking', 'food', 'kitchen', 'cook', 'bake', 'meal', 'dish']
        }
        
        text_lower = text_for_analysis.lower()
        theme_scores = {}
        
        for theme, keywords in themes.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        return 'general'
    
    def _analyze_content_style(self, descriptions):
        """Analyze the writing style of video descriptions"""
        if not descriptions:
            return "casual"
        
        combined_text = ' '.join(descriptions)
        text_lower = combined_text.lower()
        
        # Simple style detection based on keywords and patterns
        formal_indicators = ['please', 'thank you', 'we', 'our', 'welcome', 'subscribe']
        casual_indicators = ['hey', 'guys', 'what\'s up', 'yo', 'lol', 'btw', 'omg']
        
        formal_score = sum(text_lower.count(indicator) for indicator in formal_indicators)
        casual_score = sum(text_lower.count(indicator) for indicator in casual_indicators)
        
        if casual_score > formal_score:
            return "casual"
        elif formal_score > casual_score:
            return "formal"
        else:
            return "balanced"

class ScriptGenerator:
    def __init__(self):
        self.model = model
    
    def generate_script(self, topic, channel_analysis, script_length="medium"):
        """Generate a YouTube script based on channel analysis"""
        
        # Prepare the prompt based on channel analysis
        prompt = self._build_prompt(topic, channel_analysis, script_length)
        
        try:
            response = self.model.generate_content(prompt)
            script_content = response.text
            
            # Save generated script
            script_data = {
                'topic': topic,
                'channel_id': channel_analysis.get('channel_id'),
                'script_content': script_content,
                'script_length': script_length,
                'generated_at': datetime.utcnow(),
                'channel_theme': channel_analysis.get('channel_theme'),
                'content_style': channel_analysis.get('content_style')
            }
            
            scripts_collection.insert_one(script_data)
            
            return {
                'success': True,
                'script': script_content,
                'metadata': {
                    'topic': topic,
                    'length': script_length,
                    'style': channel_analysis.get('content_style', 'balanced'),
                    'theme': channel_analysis.get('channel_theme', 'general')
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_prompt(self, topic, analysis, script_length):
        """Build the prompt for script generation"""
        
        length_guidelines = {
            "short": "3-5 minutes (approximately 450-750 words)",
            "medium": "8-12 minutes (approximately 1200-1800 words)", 
            "long": "15-20 minutes (approximately 2250-3000 words)"
        }
        
        style_description = {
            "casual": "casual, friendly, and conversational tone with personal anecdotes",
            "formal": "professional, informative, and structured approach",
            "balanced": "mix of professional information with friendly, approachable delivery"
        }
        
        common_words = [word for word, count in analysis.get('common_title_words', [])[:10]]
        recent_titles = analysis.get('recent_titles', [])[:5]
        channel_theme = analysis.get('channel_theme', 'general')
        content_style = analysis.get('content_style', 'balanced')
        
        prompt = f"""
Create a YouTube video script on the topic: "{topic}"

CHANNEL ANALYSIS:
- Channel Theme: {channel_theme}
- Content Style: {style_description.get(content_style, content_style)}
- Common Keywords Used: {', '.join(common_words)}
- Recent Video Titles for Reference: {', '.join(recent_titles)}
- Target Length: {length_guidelines.get(script_length, length_guidelines['medium'])}

SCRIPT REQUIREMENTS:
1. Write in the identified content style ({content_style})
2. Include elements typical of {channel_theme} content
3. Structure: Hook → Introduction → Main Content → Conclusion → Call to Action
4. Include natural speaking cues and transitions
5. Add engagement prompts (questions for audience, comments, likes)
6. Use similar vocabulary and tone as the analyzed channel
7. Include timestamps for major sections
8. Add notes for visual elements or B-roll suggestions

SCRIPT FORMAT:
[HOOK - 0:00-0:15]
[Strong opening that grabs attention]

[INTRODUCTION - 0:15-0:45]
[Introduce yourself, topic, and what viewers will learn]

[MAIN CONTENT - 0:45-X:XX]
[Core content divided into clear sections with timestamps]

[CONCLUSION - X:XX-X:XX]
[Summarize key points]

[CALL TO ACTION - X:XX-END]
[Subscribe, like, comment prompts]

Please generate a complete, ready-to-use script that matches the analyzed channel's style and theme.
"""
        
        return prompt

# Initialize analyzers
youtube_analyzer = YouTubeAnalyzer()
script_generator = ScriptGenerator()

@app.route('/')
def index():
    return render_template('youtube_script.html')

@app.route('/api/analyze-channel', methods=['POST'])
@rate_limit(max_calls=10, period=300)  # 10 requests per 5 minutes
def analyze_channel():
    try:
        data = request.get_json()
        channel_input = data.get('channel_url', '').strip()
        
        if not channel_input:
            return jsonify({'error': 'Channel URL or handle is required'}), 400
        
        # Extract channel ID
        channel_id = youtube_analyzer.extract_channel_id(channel_input)
        if not channel_id:
            return jsonify({'error': 'Invalid channel URL or handle'}), 400
        
        # Get channel information
        channel_info = youtube_analyzer.get_channel_info(channel_id)
        if not channel_info:
            return jsonify({'error': 'Channel not found or inaccessible'}), 404
        
        # Get recent videos
        videos = youtube_analyzer.get_recent_videos(channel_id)
        if not videos:
            return jsonify({'error': 'No videos found for this channel'}), 404
        
        # Analyze channel style
        analysis = youtube_analyzer.analyze_channel_style(channel_info, videos)
        
        return jsonify({
            'success': True,
            'channel_info': {
                'title': channel_info['title'],
                'description': channel_info['description'][:200] + '...' if len(channel_info['description']) > 200 else channel_info['description'],
                'subscriber_count': channel_info['subscriber_count'],
                'video_count': channel_info['video_count'],
                'thumbnail': channel_info['thumbnail']
            },
            'analysis': {
                'channel_theme': analysis['channel_theme'],
                'content_style': analysis['content_style'],
                'total_videos_analyzed': analysis['total_videos_analyzed'],
                'common_topics': [word for word, count in analysis['common_title_words'][:10]],
                'average_title_length': round(analysis['average_title_length']),
                'recent_titles': analysis['recent_titles'][:5]
            },
            'channel_id': channel_id
        })
        
    except Exception as e:
        logger.error(f"Error in analyze_channel: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/generate-script', methods=['POST'])
@rate_limit(max_calls=5, period=300)  # 5 requests per 5 minutes
def generate_script():
    try:
        data = request.get_json()
        channel_id = data.get('channel_id')
        topic = data.get('topic', '').strip()
        script_length = data.get('length', 'medium')
        
        if not channel_id or not topic:
            return jsonify({'error': 'Channel ID and topic are required'}), 400
        
        # Get cached channel analysis
        channel_info = channels_collection.find_one({'channel_id': channel_id})
        if not channel_info:
            return jsonify({'error': 'Channel analysis not found. Please analyze the channel first.'}), 404
        
        # Get cached videos for analysis
        videos = list(videos_collection.find({'channel_id': channel_id}).sort('published_at', -1).limit(50))
        if not videos:
            return jsonify({'error': 'No video data found for analysis'}), 404
        
        # Generate analysis for script generation
        analysis = youtube_analyzer.analyze_channel_style(channel_info, videos)
        analysis['channel_id'] = channel_id
        
        # Generate script
        result = script_generator.generate_script(topic, analysis, script_length)
        
        if result['success']:
            return jsonify({
                'success': True,
                'script': result['script'],
                'metadata': result['metadata']
            })
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        logger.error(f"Error in generate_script: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)