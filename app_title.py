import os
import json
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session
from pymongo import MongoClient
import google.generativeai as genai
from googleapiclient.discovery import build
from collections import Counter, defaultdict
import re
from functools import lru_cache
import time
import statistics
from textstat import flesch_reading_ease

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'zRx$W2tGkB%h9m!Lr7@pVjC3fN6zA#XeUvQy1o8dTbKs')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', 'AIzaSyA6gva6wCYGgQpJ-C9yjgKEywLAHQnv8lE')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBv0as18PeTSsK9MS92noc3j3HVYSDC2vM')
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://kayyp118:G0Ao9pID8IULTFJZ@evscooter.jvhwand.mongodb.net/evscooter')
DB_NAME = os.getenv('MONGODB_DB_NAME', 'youtube_outliers')

# Initialize APIs
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
trends_collection = db.trends
titles_collection = db.generated_titles
performance_collection = db.title_performance

class YouTubeTrendAnalyzer:
    def __init__(self):
        self.trending_keywords = []
        self.trending_topics = []
        self.category_mapping = {
            'Technology': '28',
            'Gaming': '20',
            'Entertainment': '24',
            'Education': '27',
            'Music': '10',
            'Comedy': '23',
            'News': '25',
            'Sports': '17',
            'Film': '1',
            'Autos': '2'
        }
        
    def get_multiple_trending_sources(self, region_code='US', category='General'):
        """Fetch trending videos from multiple sources and categories"""
        all_videos = []
        
        # Get general trending
        videos = self.get_trending_videos(region_code, '0')
        all_videos.extend(videos)
        
        # Get category-specific trending if specified
        if category != 'General' and category in self.category_mapping:
            cat_videos = self.get_trending_videos(region_code, self.category_mapping[category])
            all_videos.extend(cat_videos)
        
        # Get recent viral videos (high view velocity)
        viral_videos = self.get_viral_videos()
        all_videos.extend(viral_videos)
        
        return all_videos
    
    def get_viral_videos(self):
        """Get recently viral videos based on view velocity"""
        try:
            # Search for recent videos with high engagement
            search_request = youtube.search().list(
                part='snippet',
                order='viewCount',
                publishedAfter=(datetime.now() - timedelta(days=7)).isoformat() + 'Z',
                maxResults=25,
                type='video'
            )
            search_response = search_request.execute()
            
            video_ids = [item['id']['videoId'] for item in search_response['items']]
            
            # Get detailed stats for these videos
            videos_request = youtube.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()
            
            return videos_response['items']
        except Exception as e:
            print(f"Error fetching viral videos: {e}")
            return []
    
    @lru_cache(maxsize=32)
    def get_trending_videos(self, region_code='US', category_id='0'):
        """Fetch trending videos from YouTube API with caching"""
        try:
            request = youtube.videos().list(
                part='snippet,statistics',
                chart='mostPopular',
                regionCode=region_code,
                maxResults=50,
                videoCategoryId=category_id
            )
            response = request.execute()
            return response['items']
        except Exception as e:
            print(f"Error fetching trending videos: {e}")
            return []
    
    def analyze_advanced_patterns(self, videos):
        """Advanced pattern analysis of trending titles"""
        patterns = {
            'questions': 0,
            'numbers': 0,
            'caps_words': 0,
            'emotional_words': 0,
            'avg_length': 0,
            'exclamation_marks': 0,
            'brackets_parentheses': 0,
            'vs_comparisons': 0,
            'time_indicators': 0,
            'personal_pronouns': 0,
            'power_words': 0,
            'urgency_words': 0,
            'readability_score': 0
        }
        
        # Enhanced word lists
        emotional_words = [
            'amazing', 'incredible', 'shocking', 'unbelievable', 'crazy', 'insane', 
            'epic', 'awesome', 'mind-blowing', 'viral', 'trending', 'hot', 'new', 
            'latest', 'breaking', 'exclusive', 'secret', 'hidden', 'revealed', 
            'exposed', 'truth', 'real', 'fake', 'destroyed', 'roasted', 'savage'
        ]
        
        power_words = [
            'ultimate', 'best', 'worst', 'top', 'proven', 'guaranteed', 'free',
            'easy', 'quick', 'instant', 'powerful', 'effective', 'professional',
            'expert', 'advanced', 'complete', 'comprehensive', 'exclusive'
        ]
        
        urgency_words = [
            'now', 'today', 'urgent', 'limited', 'last', 'final', 'ending',
            'deadline', 'hurry', 'quick', 'fast', 'immediate', 'instant'
        ]
        
        time_indicators = [
            '2024', '2025', 'today', 'yesterday', 'tomorrow', 'week', 'month',
            'year', 'recent', 'latest', 'new', 'updated', 'current'
        ]
        
        personal_pronouns = ['i', 'you', 'we', 'my', 'your', 'our', 'me', 'us']
        
        total_length = 0
        readability_scores = []
        
        for video in videos:
            title = video['snippet']['title'].lower()
            original_title = video['snippet']['title']
            
            # Basic patterns
            if '?' in title:
                patterns['questions'] += 1
            if any(char.isdigit() for char in title):
                patterns['numbers'] += 1
            if any(word.isupper() for word in original_title.split()):
                patterns['caps_words'] += 1
            if '!' in title:
                patterns['exclamation_marks'] += 1
            if any(char in title for char in '()[]{}'):
                patterns['brackets_parentheses'] += 1
            if ' vs ' in title or ' versus ' in title:
                patterns['vs_comparisons'] += 1
            
            # Word-based analysis
            words = title.split()
            if any(word in emotional_words for word in words):
                patterns['emotional_words'] += 1
            if any(word in power_words for word in words):
                patterns['power_words'] += 1
            if any(word in urgency_words for word in words):
                patterns['urgency_words'] += 1
            if any(word in time_indicators for word in words):
                patterns['time_indicators'] += 1
            if any(word in personal_pronouns for word in words):
                patterns['personal_pronouns'] += 1
            
            total_length += len(original_title)
            
            # Readability score
            try:
                readability_scores.append(flesch_reading_ease(original_title))
            except:
                readability_scores.append(50)  # Default score
        
        if videos:
            patterns['avg_length'] = total_length // len(videos)
            patterns['readability_score'] = statistics.mean(readability_scores)
            
            # Convert counts to percentages
            video_count = len(videos)
            for key in ['questions', 'numbers', 'caps_words', 'emotional_words', 
                       'exclamation_marks', 'brackets_parentheses', 'vs_comparisons',
                       'time_indicators', 'personal_pronouns', 'power_words', 'urgency_words']:
                patterns[key] = round((patterns[key] / video_count) * 100, 1)
        
        return patterns
    
    def extract_contextual_keywords(self, videos, niche='General'):
        """Extract keywords with context and relevance scoring"""
        all_titles = [video['snippet']['title'] for video in videos]
        
        # Enhanced stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
            'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 
            'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'video', 'youtube', 'subscribe', 'like', 'comment', 'share'
        }
        
        # Extract phrases (2-3 word combinations)
        phrases = []
        words = []
        
        for title in all_titles:
            title_words = re.findall(r'\b[a-zA-Z]+\b', title.lower())
            clean_words = [word for word in title_words if word not in stop_words and len(word) > 2]
            words.extend(clean_words)
            
            # Extract 2-word phrases
            for i in range(len(clean_words) - 1):
                phrase = f"{clean_words[i]} {clean_words[i+1]}"
                phrases.append(phrase)
        
        # Count frequencies
        word_freq = Counter(words)
        phrase_freq = Counter(phrases)
        
        # Combine and score
        trending_terms = []
        
        # Add top words
        for word, count in word_freq.most_common(15):
            trending_terms.append((word, count, 'word'))
        
        # Add top phrases
        for phrase, count in phrase_freq.most_common(10):
            if count >= 2:  # Only include phrases that appear multiple times
                trending_terms.append((phrase, count, 'phrase'))
        
        # Sort by frequency
        trending_terms.sort(key=lambda x: x[1], reverse=True)
        
        return trending_terms[:25]
    
    def get_channel_insights(self, videos):
        """Analyze successful channels and their title strategies"""
        channel_data = defaultdict(list)
        
        for video in videos:
            channel_name = video['snippet']['channelTitle']
            title = video['snippet']['title']
            views = int(video['statistics'].get('viewCount', 0))
            
            channel_data[channel_name].append({
                'title': title,
                'views': views,
                'title_length': len(title)
            })
        
        channel_insights = {}
        for channel, data in channel_data.items():
            if len(data) >= 2:  # Only analyze channels with multiple trending videos
                avg_views = statistics.mean([v['views'] for v in data])
                avg_length = statistics.mean([v['title_length'] for v in data])
                
                channel_insights[channel] = {
                    'avg_views': avg_views,
                    'avg_title_length': avg_length,
                    'trending_count': len(data),
                    'sample_titles': [v['title'] for v in data[:3]]
                }
        
        return dict(sorted(channel_insights.items(), 
                          key=lambda x: x[1]['avg_views'], reverse=True)[:10])
    
    def get_comprehensive_trends(self, region_code='US', category='General'):
        """Get comprehensive trend analysis"""
        # Check if we have recent cached data (within 2 hours)
        cache_key = f"{region_code}_{category}_{datetime.now().strftime('%Y-%m-%d_%H')}"
        cached_trends = trends_collection.find_one({'cache_key': cache_key})
        
        if cached_trends and 'data' in cached_trends:
            return cached_trends['data']
        
        # Fetch fresh data
        trending_videos = self.get_multiple_trending_sources(region_code, category)
        if not trending_videos:
            return None
        
        # Remove duplicates
        seen_titles = set()
        unique_videos = []
        for video in trending_videos:
            title = video['snippet']['title']
            if title not in seen_titles:
                seen_titles.add(title)
                unique_videos.append(video)
        
        # Comprehensive analysis
        keywords = self.extract_contextual_keywords(unique_videos, category)
        patterns = self.analyze_advanced_patterns(unique_videos)
        channel_insights = self.get_channel_insights(unique_videos)
        
        # Performance metrics
        views = [int(v['statistics'].get('viewCount', 0)) for v in unique_videos]
        engagement_rates = []
        
        for video in unique_videos:
            stats = video['statistics']
            views_count = int(stats.get('viewCount', 0))
            likes_count = int(stats.get('likeCount', 0))
            comments_count = int(stats.get('commentCount', 0))
            
            if views_count > 0:
                engagement = ((likes_count + comments_count) / views_count) * 100
                engagement_rates.append(engagement)
        
        trends_data = {
            'keywords': keywords,
            'patterns': patterns,
            'channel_insights': channel_insights,
            'sample_titles': [video['snippet']['title'] for video in unique_videos[:15]],
            'performance_metrics': {
                'avg_views': statistics.mean(views) if views else 0,
                'median_views': statistics.median(views) if views else 0,
                'avg_engagement_rate': statistics.mean(engagement_rates) if engagement_rates else 0
            },
            'timestamp': datetime.now().isoformat(),
            'total_videos_analyzed': len(unique_videos)
        }
        
        # Cache the results
        trends_collection.insert_one({
            'cache_key': cache_key,
            'region': region_code,
            'category': category,
            'data': trends_data,
            'created_at': datetime.now()
        })
        
        return trends_data

class EnhancedTitleGenerator:
    def __init__(self):
        self.analyzer = YouTubeTrendAnalyzer()
        self.title_templates = {
            'question': [
                "Why {keyword}?",
                "How to {action} {keyword}?",
                "What if {scenario}?",
                "Is {topic} {adjective}?"
            ],
            'list': [
                "{number} {adjective} {keyword} {timeframe}",
                "Top {number} {category} You {action}",
                "{number} Reasons Why {statement}"
            ],
            'how_to': [
                "How to {action} {object} in {timeframe}",
                "The {adjective} Way to {action}",
                "{action} Like a {expert_level}"
            ],
            'emotional': [
                "This {object} Will {emotion_verb} You",
                "You Won't Believe {statement}",
                "The {adjective} {object} Ever"
            ]
        }
    
    def generate_advanced_titles(self, client_prompt, niche, target_audience, style_preference, count=5):
        """Generate titles using advanced AI prompting and trend analysis"""
        
        # Get comprehensive trends
        trends = self.analyzer.get_comprehensive_trends('US', niche)
        if not trends:
            return {"error": "Unable to fetch current trends"}
        
        # Extract top trending terms
        top_keywords = [item[0] for item in trends['keywords'][:8] if item[2] == 'word']
        top_phrases = [item[0] for item in trends['keywords'][:5] if item[2] == 'phrase']
        
        # Analyze successful patterns
        patterns = trends['patterns']
        sample_titles = trends['sample_titles'][:8]
        
        # Create enhanced prompt
        prompt = self._create_enhanced_prompt(
            client_prompt, niche, target_audience, style_preference, count,
            top_keywords, top_phrases, patterns, sample_titles, trends
        )
        
        try:
            # Generate titles with multiple attempts for better results
            all_titles = []
            for attempt in range(2):  # Generate twice and pick best
                response = model.generate_content(prompt)
                titles = self._parse_generated_titles(response.text)
                all_titles.extend(titles)
            
            # Score and select best titles
            scored_titles = self._score_titles(all_titles, trends, client_prompt, niche)
            final_titles = [title for title, score, _ in scored_titles[:count]]
            
            # Save to database
            self._save_generation_record(
                client_prompt, niche, target_audience, style_preference,
                final_titles, trends, scored_titles
            )
            
            return {
                'titles': final_titles,
                'trends_context': {
                    'trending_keywords': trends['keywords'][:8],
                    'patterns_used': patterns,
                    'performance_prediction': self._predict_performance(scored_titles[:count], trends)
                },
                'generation_insights': {
                    'total_generated': len(all_titles),
                    'selection_method': 'AI Scoring + Trend Analysis',
                    'confidence_score': self._calculate_confidence(scored_titles[:count])
                }
            }
            
        except Exception as e:
            return {"error": f"Error generating titles: {str(e)}"}
    
    def _create_enhanced_prompt(self, client_prompt, niche, target_audience, style_preference, 
                               count, keywords, phrases, patterns, samples, trends):
        """Create a sophisticated prompt for AI title generation"""
        
        return f"""
        You are an expert YouTube title strategist with deep knowledge of viral content patterns and audience psychology.

        GENERATION TASK:
        Create {count * 2} highly engaging YouTube titles for: "{client_prompt}"
        
        TARGET SPECIFICATIONS:
        - Niche: {niche}
        - Audience: {target_audience}  
        - Style: {style_preference}

        CURRENT TREND INTELLIGENCE:
        Top Keywords: {', '.join(keywords)}
        Trending Phrases: {', '.join(phrases)}
        
        VIRAL PATTERN ANALYSIS:
        - Optimal Length: {patterns['avg_length']} characters (aim for 45-65)
        - Questions: {patterns['questions']}% of viral titles use questions
        - Numbers: {patterns['numbers']}% include specific numbers
        - Emotional Words: {patterns['emotional_words']}% use emotional triggers
        - Power Words: {patterns['power_words']}% include authority words
        - Urgency: {patterns['urgency_words']}% create urgency
        - Personal Pronouns: {patterns['personal_pronouns']}% use "you/your/my"

        SUCCESSFUL TITLE EXAMPLES:
        {chr(10).join([f"• {title}" for title in samples])}

        ADVANCED TITLE STRATEGIES:
        1. Hook + Promise: Create curiosity then deliver value
        2. Emotional Trigger: Tap into surprise, fear, joy, anger, or anticipation  
        3. Social Proof: Imply popularity or authority
        4. Specificity: Use exact numbers, timeframes, or methods
        5. Benefit-Driven: Clear value proposition for viewer
        6. Pattern Interrupt: Unexpected angle or contrarian view

        PSYCHOLOGICAL TRIGGERS:
        - Curiosity Gap: "The [adjective] [method] that [outcome]"
        - FOMO: "Everyone is [doing this] except you"
        - Authority: "Experts don't want you to know [secret]"
        - Transformation: "From [problem] to [solution]"
        - Controversy: "[Unpopular opinion] about [topic]"

        TITLE GENERATION RULES:
        ✓ Incorporate 1-2 trending keywords naturally
        ✓ Match the {style_preference} style authentically
        ✓ Optimize for {target_audience} language and interests
        ✓ Create immediate curiosity without being clickbait
        ✓ Use active voice and strong verbs
        ✓ Include emotional or power words strategically
        ✓ Ensure relevance to "{client_prompt}"
        ✓ Vary title structures for diversity

        ✗ Avoid generic or boring language
        ✗ Don't stuff keywords unnaturally  
        ✗ No misleading or false promises
        ✗ Avoid overly complex words for general audiences
        ✗ Don't ignore niche-specific terminology when relevant

        OUTPUT FORMAT:
        Generate exactly {count * 2} titles, each on a new line, numbered 1-{count * 2}.
        Focus on creating titles that would genuinely perform well on YouTube today.
        """
    
    def _parse_generated_titles(self, response_text):
        """Parse and clean generated titles"""
        lines = response_text.strip().split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            if line and not line.isdigit():
                # Remove numbering
                title = re.sub(r'^\d+\.?\s*', '', line)
                title = title.strip()
                if title and len(title) > 10:  # Basic validation
                    titles.append(title)
        
        return titles
    
    def _score_titles(self, titles, trends, client_prompt, niche):
        """Score titles based on multiple factors"""
        scored_titles = []
        
        for title in titles:
            score = 0
            factors = {}
            
            # Length optimization (45-65 characters ideal)
            length = len(title)
            if 45 <= length <= 65:
                length_score = 100
            elif 35 <= length <= 75:
                length_score = 80
            else:
                length_score = max(0, 100 - abs(length - 55) * 2)
            
            factors['length'] = length_score
            score += length_score * 0.15
            
            # Keyword relevance
            title_lower = title.lower()
            prompt_lower = client_prompt.lower()
            
            # Check for trending keywords
            trending_score = 0
            for keyword, freq, type_ in trends['keywords'][:10]:
                if keyword.lower() in title_lower:
                    trending_score += freq * (2 if type_ == 'phrase' else 1)
            
            factors['trending'] = min(100, trending_score * 5)
            score += factors['trending'] * 0.25
            
            # Relevance to client prompt
            prompt_words = set(prompt_lower.split())
            title_words = set(title_lower.split())
            relevance = len(prompt_words.intersection(title_words)) / len(prompt_words) * 100
            
            factors['relevance'] = relevance
            score += relevance * 0.2
            
            # Pattern matching (questions, numbers, emotional words)
            pattern_score = 0
            if '?' in title:
                pattern_score += 20
            if any(char.isdigit() for char in title):
                pattern_score += 15
            
            emotional_words = ['amazing', 'incredible', 'secret', 'revealed', 'shocking', 'epic']
            if any(word in title_lower for word in emotional_words):
                pattern_score += 25
            
            factors['patterns'] = pattern_score
            score += pattern_score * 0.15
            
            # Readability and clarity
            word_count = len(title.split())
            readability_score = 100 if 6 <= word_count <= 12 else max(0, 100 - abs(word_count - 9) * 8)
            
            factors['readability'] = readability_score
            score += readability_score * 0.1
            
            # Uniqueness (avoid duplicates)
            uniqueness = 100  # Could implement similarity checking
            factors['uniqueness'] = uniqueness
            score += uniqueness * 0.15
            
            scored_titles.append((title, score, factors))
        
        # Sort by score and remove duplicates
        scored_titles.sort(key=lambda x: x[1], reverse=True)
        seen_titles = set()
        unique_scored = []
        
        for title, score, factors in scored_titles:
            if title.lower() not in seen_titles:
                seen_titles.add(title.lower())
                unique_scored.append((title, score, factors))
        
        return unique_scored
    
    def _predict_performance(self, scored_titles, trends):
        """Predict potential performance of generated titles"""
        predictions = []
        
        for title, score, factors in scored_titles:  # Fixed: Unpack all three elements
            # Simple performance prediction based on score and trends
            base_performance = score / 100
            
            # Adjust based on trend alignment
            trend_boost = factors.get('trending', 0) / 100 * 0.3
            
            predicted_ctr = min(0.15, base_performance * 0.1 + trend_boost)  # Cap at 15% CTR
            predicted_views = int(trends['performance_metrics']['avg_views'] * base_performance)
            
            predictions.append({
                'title': title,
                'predicted_ctr': f"{predicted_ctr:.2%}",
                'predicted_views': f"{predicted_views:,}",
                'confidence': 'High' if score > 80 else 'Medium' if score > 60 else 'Low'
            })
        
        return predictions
    
    def _calculate_confidence(self, scored_titles):
        """Calculate overall confidence in generated titles"""
        if not scored_titles:
            return 0
        
        avg_score = sum(score for _, score, _ in scored_titles) / len(scored_titles)
        return min(100, int(avg_score))
    
    def _save_generation_record(self, client_prompt, niche, target_audience, style_preference,
                               final_titles, trends, all_scored_titles):
        """Save generation record with detailed analytics"""
        record = {
            'client_prompt': client_prompt,
            'niche': niche,
            'target_audience': target_audience,
            'style_preference': style_preference,
            'generated_titles': final_titles,
            'all_candidates': [
                {'title': title, 'score': score, 'factors': factors}
                for title, score, factors in all_scored_titles[:20]
            ],
            'trends_snapshot': {
                'keywords': trends['keywords'][:5],
                'patterns': trends['patterns'],
                'total_videos_analyzed': trends['total_videos_analyzed']
            },
            'timestamp': datetime.now().isoformat(),
            'generation_version': '2.0'
        }
        
        titles_collection.insert_one(record)

# Initialize the enhanced title generator
title_generator = EnhancedTitleGenerator()

# Updated Flask routes
@app.route('/')
def index():
    return render_template('youtube_title.html')

@app.route('/generate', methods=['POST'])
def generate_titles():
    data = request.get_json()
    
    client_prompt = data.get('client_prompt', '')
    niche = data.get('niche', 'General')
    target_audience = data.get('target_audience', 'General Audience')
    style_preference = data.get('style_preference', 'Engaging')
    count = int(data.get('count', 5))
    
    if not client_prompt:
        return jsonify({'error': 'Client prompt is required'}), 400
    
    result = title_generator.generate_advanced_titles(
        client_prompt, niche, target_audience, style_preference, count
    )
    
    return jsonify(result)

@app.route('/trends')
def get_trends():
    """Get current trending data"""
    analyzer = YouTubeTrendAnalyzer()
    trends = analyzer.get_comprehensive_trends()
    return jsonify(trends)

@app.route('/trends/<category>')
def get_category_trends(category):
    """Get trends for specific category"""
    analyzer = YouTubeTrendAnalyzer()
    trends = analyzer.get_comprehensive_trends('US', category)
    return jsonify(trends)

@app.route('/history')
def get_history():
    """Get generation history with analytics"""
    history = list(titles_collection.find().sort('timestamp', -1).limit(20))
    for item in history:
        item['_id'] = str(item['_id'])
    return jsonify(history)

@app.route('/performance/<title_id>')
def get_title_performance(title_id):
    """Get performance data for a specific title"""
    # This would integrate with YouTube Analytics API in production
    return jsonify({"message": "Performance tracking coming soon"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)