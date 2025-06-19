# from youtube_service import YouTubeService
# from database import Database
# import time

# class OutlierDetector:
#     def __init__(self):
#         self.youtube_service = YouTubeService()
#         self.database = Database()
    
#     def detect_outliers(self, query, filters=None):
#         """Main function to detect outlier videos"""
#         if filters is None:
#             filters = {}
        
#         print(f"🔍 Searching for videos: {query}")
        
#         # Step 1: Search for videos
#         videos = self._get_videos_for_query(query)
#         if not videos:
#             return []
        
#         print(f"📹 Found {len(videos)} videos")
        
#         # Step 2: Get video statistics
#         video_ids = [v['video_id'] for v in videos]
#         video_stats = self.youtube_service.get_video_stats(video_ids)
        
#         # Step 3: Calculate multipliers
#         outlier_videos = []
#         processed_channels = {}
        
#         for video in videos:
#             video_id = video['video_id']
#             channel_id = video['channel_id']
            
#             # Skip if video stats not available or video is private
#             if video_id not in video_stats:
#                 continue
            
#             video_views = video_stats[video_id]['views']
            
#             # Get channel average views (with caching)
#             if channel_id not in processed_channels:
#                 channel_avg = self._get_channel_average_views(channel_id)
#                 processed_channels[channel_id] = channel_avg
#             else:
#                 channel_avg = processed_channels[channel_id]
            
#             if channel_avg == 0:
#                 continue
            
#             # Calculate multiplier
#             multiplier = video_views / channel_avg
            
#             # Create video result
#             video_result = {
#                 'video_id': video_id,
#                 'title': video['title'],
#                 'channel_title': video['channel_title'],
#                 'channel_id': channel_id,
#                 'views': video_views,
#                 'channel_avg_views': channel_avg,
#                 'multiplier': round(multiplier, 2),
#                 'likes': video_stats[video_id]['likes'],
#                 'comments': video_stats[video_id]['comments'],
#                 'duration': video_stats[video_id]['duration'],
#                 'duration_seconds': self.youtube_service.parse_duration(video_stats[video_id]['duration']),
#                 'published_at': video['published_at'],
#                 'url': f"https://www.youtube.com/watch?v={video_id}"
#             }
            
#             # Apply filters
#             if self._passes_filters(video_result, filters):
#                 outlier_videos.append(video_result)
        
#         # Sort by multiplier descending
#         outlier_videos.sort(key=lambda x: x['multiplier'], reverse=True)
        
#         # Save search history
#         self.database.save_search_history(query, len(outlier_videos), filters)
        
#         print(f"🎯 Found {len(outlier_videos)} outlier videos")
#         return outlier_videos
    
#     def _get_videos_for_query(self, query):
#         """Get videos for query (check cache first)"""
#         # Check cache first
#         cached_videos = self.database.get_cached_search_results(query)
#         if cached_videos:
#             print("📦 Using cached search results")
#             return cached_videos
        
#         # Search YouTube API
#         videos = self.youtube_service.search_videos(query)
        
#         # Cache the results
#         for video in videos:
#             self.database.cache_video_data(video, query)
        
#         return videos
    
#     def _get_channel_average_views(self, channel_id):
#         """Get channel average views (with caching)"""
#         # Check cache first
#         cached_channel = self.database.get_cached_channel_data(channel_id)
#         if cached_channel and 'average_views' in cached_channel:
#             return cached_channel['average_views']
        
#         # Calculate from YouTube API
#         print(f"📊 Calculating average views for channel: {channel_id}")
#         average_views = self.youtube_service.calculate_channel_average_views(channel_id)
        
#         # Get additional channel info
#         channel_info = self.youtube_service.get_channel_info(channel_id)
#         if channel_info:
#             channel_data = {
#                 'average_views': average_views,
#                 'subscriber_count': channel_info['subscriber_count'],
#                 'video_count': channel_info['video_count'],
#                 'view_count': channel_info['view_count'],
#                 'title': channel_info['title']
#             }
            
#             # Cache the result
#             self.database.cache_channel_data(channel_id, channel_data)
        
#         return average_views
    
#     def _passes_filters(self, video, filters):
#         """Check if video passes all filters"""
#         # Multiplier filter
#         min_multiplier = filters.get('min_multiplier', 1.0)
#         max_multiplier = filters.get('max_multiplier', 500.0)
#         if not (min_multiplier <= video['multiplier'] <= max_multiplier):
#             return False
        
#         # Views filter
#         min_views = filters.get('min_views', 0)
#         max_views = filters.get('max_views', float('inf'))
#         if not (min_views <= video['views'] <= max_views):
#             return False
        
#         # Duration filter (in seconds)
#         min_duration = filters.get('min_duration_seconds', 0)
#         max_duration = filters.get('max_duration_seconds', float('inf'))
#         if not (min_duration <= video['duration_seconds'] <= max_duration):
#             return False
        
#         # Channel subscribers filter (requires additional API call)
#         min_subscribers = filters.get('min_subscribers')
#         max_subscribers = filters.get('max_subscribers')
#         if min_subscribers is not None or max_subscribers is not None:
#             channel_data = self.database.get_cached_channel_data(video['channel_id'])
#             if channel_data and 'subscriber_count' in channel_data:
#                 subscriber_count = channel_data['subscriber_count']
#                 if min_subscribers is not None and subscriber_count < min_subscribers:
#                     return False
#                 if max_subscribers is not None and subscriber_count > max_subscribers:
#                     return False
        
#         return True
    
#     def get_search_statistics(self):
#         """Get search statistics and popular queries"""
#         return {
#             'popular_searches': self.database.get_popular_searches(),
#             'total_searches': self.database.searches_collection.count_documents({})
#         }
    
#     def format_number(self, num):
#         """Format large numbers for display"""
#         if num >= 1000000:
#             return f"{num/1000000:.1f}M"
#         elif num >= 1000:
#             return f"{num/1000:.1f}K"
#         else:
#             return str(num) 

from youtube_service import YouTubeService
from database import Database
import time
import re
from collections import defaultdict
from datetime import datetime, timedelta

class OutlierDetector:
    def __init__(self):
        self.youtube_service = YouTubeService()
        self.database = Database()
        self.api_calls_count = 0
        self.max_api_calls = 9000  # Conservative limit to stay under 10k quota
        
        # Global language and region mappings for comprehensive search
        self.global_search_params = {
            'regions': ['US', 'IN', 'GB', 'CA', 'AU', 'DE', 'FR', 'ES', 'BR', 'JP', 'KR', 'RU'],
            'languages': ['en', 'hi', 'es', 'pt', 'fr', 'de', 'ja', 'ko', 'ru', 'ar'],
            'content_types': ['video', 'channel', 'playlist']
        }
    
    def detect_outliers(self, query, filters=None):
        """Enhanced main function to detect outlier videos with global analysis"""
        if filters is None:
            filters = {}
        
        print(f"🔍 Starting enhanced global search for: {query}")
        
        # Step 1: Generate related search queries for broader coverage
        related_queries = self._generate_related_queries(query)
        print(f"🌍 Generated {len(related_queries)} related queries for global search")
        
        # Step 2: Collect videos from multiple sources
        all_videos = []
        
        # Original query
        videos = self._get_videos_for_query(query, enhanced=True)
        all_videos.extend(videos)
        
        # Related queries (limit to prevent quota exhaustion)
        for related_query in related_queries[:3]:  # Limit to 3 related queries
            if self._check_api_quota():
                related_videos = self._get_videos_for_query(related_query, enhanced=True)
                all_videos.extend(related_videos)
            else:
                print("⚠️ API quota limit approaching, stopping related searches")
                break
        
        # Remove duplicates
        unique_videos = self._remove_duplicate_videos(all_videos)
        print(f"📹 Found {len(unique_videos)} unique videos across all searches")
        
        if not unique_videos:
            return []
        
        # Step 3: Enhanced video analysis with batch processing
        outlier_videos = self._analyze_videos_advanced(unique_videos, query, filters)
        
        # Step 4: Advanced filtering and scoring
        scored_videos = self._calculate_advanced_scores(outlier_videos)
        
        # Step 5: Final ranking with multiple criteria
        final_results = self._rank_videos_multi_criteria(scored_videos)
        
        # Save enhanced search history
        self.database.save_search_history(query, len(final_results), {
            **filters,
            'related_queries': related_queries,
            'total_videos_analyzed': len(unique_videos),
            'api_calls_used': self.api_calls_count
        })
        
        print(f"🎯 Final results: {len(final_results)} advanced outlier videos")
        print(f"📊 API calls used: {self.api_calls_count}/{self.max_api_calls}")
        
        return final_results
    
    def _generate_related_queries(self, original_query):
        """Generate related search queries for broader coverage"""
        related_queries = []
        
        # Extract key terms from original query
        key_terms = re.findall(r'\b\w+\b', original_query.lower())
        
        # Generate variations
        variations = [
            f"{original_query} explained",
            f"{original_query} analysis",
            f"{original_query} review",
            f"{original_query} reaction",
            f"{original_query} behind the scenes",
            f"{original_query} facts",
            f"{original_query} theory",
            f"{original_query} documentary"
        ]
        
        # Add single key term searches for broader reach
        if len(key_terms) > 1:
            for term in key_terms[:2]:  # Limit to prevent too many queries
                if len(term) > 3:  # Avoid very short terms
                    variations.append(term)
        
        # Filter out queries that are too similar to original
        for variation in variations:
            if variation.lower() != original_query.lower():
                related_queries.append(variation)
        
        return related_queries[:5]  # Limit to 5 related queries
    
    def _get_videos_for_query(self, query, enhanced=False):
        """Enhanced video retrieval with global parameters"""
        # Check cache first
        cached_videos = self.database.get_cached_search_results(query)
        if cached_videos and not enhanced:
            print(f"📦 Using cached results for: {query}")
            return cached_videos
        
        if not self._check_api_quota():
            print("⚠️ API quota limit reached, using cached data only")
            return cached_videos or []
        
        videos = []
        
        if enhanced:
            # Search across multiple regions for global coverage
            for region in self.global_search_params['regions'][:4]:  # Limit regions
                if not self._check_api_quota():
                    break
                    
                region_videos = self.youtube_service.search_videos(
                    query, max_results=25, region_code=region
                )
                videos.extend(region_videos)
                self.api_calls_count += 1
                
                time.sleep(0.1)  # Small delay between requests
        else:
            # Standard search
            videos = self.youtube_service.search_videos(query, max_results=50)
            self.api_calls_count += 1
        
        # Cache the raw results
        for video in videos:
            self.database.cache_video_data(video, query)
        
        return videos
    
    def _remove_duplicate_videos(self, videos):
        """Remove duplicate videos by video_id"""
        seen_ids = set()
        unique_videos = []
        
        for video in videos:
            video_id = video['video_id']
            if video_id not in seen_ids:
                seen_ids.add(video_id)
                unique_videos.append(video)
        
        return unique_videos
    
    def _analyze_videos_advanced(self, videos, original_query, filters):
        """Advanced video analysis with enhanced metrics"""
        if not self._check_api_quota():
            return []
        
        # Batch process video IDs to minimize API calls
        video_ids = [v['video_id'] for v in videos]
        video_stats = self.youtube_service.get_video_stats(video_ids)
        self.api_calls_count += len(video_ids) // 50 + 1  # Estimate API calls
        
        outlier_videos = []
        processed_channels = {}
        channel_batch = []
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video['channel_id']
            
            # Skip if video stats not available
            if video_id not in video_stats:
                continue
            
            stats = video_stats[video_id]
            
            # Batch channel processing to minimize API calls
            if channel_id not in processed_channels:
                channel_batch.append(channel_id)
        
        # Process channels in batches
        if channel_batch and self._check_api_quota():
            for channel_id in channel_batch:
                if not self._check_api_quota():
                    break
                    
                channel_avg = self._get_channel_average_views(channel_id)
                processed_channels[channel_id] = channel_avg
        
        # Analyze each video with enhanced metrics
        for video in videos:
            video_id = video['video_id']
            channel_id = video['channel_id']
            
            if video_id not in video_stats or channel_id not in processed_channels:
                continue
            
            stats = video_stats[video_id]
            channel_avg = processed_channels[channel_id]
            
            if channel_avg == 0:
                continue
            
            # Calculate multiple performance metrics
            multiplier = stats['views'] / channel_avg
            engagement_rate = self._calculate_engagement_rate(stats)
            viral_score = self._calculate_viral_score(stats, video)
            relevance_score = self._calculate_relevance_score(video, original_query)
            
            video_result = {
                'video_id': video_id,
                'title': video['title'],
                'channel_title': video['channel_title'],
                'channel_id': channel_id,
                'views': stats['views'],
                'channel_avg_views': channel_avg,
                'multiplier': round(multiplier, 2),
                'likes': stats['likes'],
                'comments': stats['comments'],
                'duration': stats['duration'],
                'duration_seconds': self.youtube_service.parse_duration(stats['duration']),
                'published_at': video['published_at'],
                'url': f"https://www.youtube.com/watch?v={video_id}",
                # Enhanced metrics
                'engagement_rate': round(engagement_rate, 4),
                'viral_score': round(viral_score, 2),
                'relevance_score': round(relevance_score, 2),
                'video_age_days': self._get_video_age_days(video['published_at'])
            }
            
            # Apply enhanced filters
            if self._passes_enhanced_filters(video_result, filters):
                outlier_videos.append(video_result)
        
        return outlier_videos
    
    def _calculate_engagement_rate(self, stats):
        """Calculate engagement rate (likes + comments) / views"""
        if stats['views'] == 0:
            return 0
        return (stats['likes'] + stats['comments']) / stats['views']
    
    def _calculate_viral_score(self, stats, video):
        """Calculate viral potential score based on multiple factors"""
        base_score = 0
        
        # Views factor (logarithmic scale)
        if stats['views'] > 0:
            base_score += min(10, (stats['views'] / 1000000) * 2)  # Max 10 points
        
        # Engagement factor
        if stats['views'] > 0:
            engagement = (stats['likes'] + stats['comments']) / stats['views']
            base_score += min(5, engagement * 1000)  # Max 5 points
        
        # Recency factor (newer videos get bonus)
        age_days = self._get_video_age_days(video['published_at'])
        if age_days <= 7:
            base_score += 3
        elif age_days <= 30:
            base_score += 1
        
        return base_score
    
    def _calculate_relevance_score(self, video, original_query):
        """Calculate relevance score based on title and query similarity"""
        title = video['title'].lower()
        query_terms = original_query.lower().split()
        
        matches = 0
        for term in query_terms:
            if term in title:
                matches += 1
        
        return (matches / len(query_terms)) * 10 if query_terms else 0
    
    def _get_video_age_days(self, published_at):
        """Calculate video age in days"""
        try:
            pub_date = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
            return (datetime.utcnow() - pub_date).days
        except:
            return 0
    
    def _calculate_advanced_scores(self, videos):
        """Calculate composite scores for ranking"""
        for video in videos:
            # Composite score combining multiple factors
            composite_score = (
                video['multiplier'] * 0.4 +          # 40% weight on view multiplier
                video['viral_score'] * 0.25 +        # 25% weight on viral potential
                video['engagement_rate'] * 1000 * 0.2 + # 20% weight on engagement
                video['relevance_score'] * 0.15       # 15% weight on relevance
            )
            
            video['composite_score'] = round(composite_score, 2)
        
        return videos
    
    def _rank_videos_multi_criteria(self, videos):
        """Rank videos using multiple criteria"""
        # Sort by composite score first, then by multiplier as tiebreaker
        videos.sort(key=lambda x: (x['composite_score'], x['multiplier']), reverse=True)
        
        # Add ranking information
        for i, video in enumerate(videos):
            video['rank'] = i + 1
            video['performance_tier'] = self._get_performance_tier(video['multiplier'])
        
        return videos
    
    def _get_performance_tier(self, multiplier):
        """Categorize video performance into tiers"""
        if multiplier >= 50:
            return "Mega Viral"
        elif multiplier >= 20:
            return "Super Viral"
        elif multiplier >= 10:
            return "Highly Viral"
        elif multiplier >= 5:
            return "Viral"
        elif multiplier >= 2:
            return "Above Average"
        else:
            return "Average"
    
    def _passes_enhanced_filters(self, video, filters):
        """Enhanced filter checking with additional criteria"""
        # Original filters
        if not self._passes_filters(video, filters):
            return False
        
        # Additional enhanced filters
        min_engagement = filters.get('min_engagement_rate', 0)
        if video['engagement_rate'] < min_engagement:
            return False
        
        min_viral_score = filters.get('min_viral_score', 0)
        if video['viral_score'] < min_viral_score:
            return False
        
        max_age_days = filters.get('max_age_days')
        if max_age_days and video['video_age_days'] > max_age_days:
            return False
        
        return True
    
    def _check_api_quota(self):
        """Check if we're within API quota limits"""
        return self.api_calls_count < self.max_api_calls
    
    def get_api_usage_stats(self):
        """Get current API usage statistics"""
        return {
            'calls_used': self.api_calls_count,
            'calls_remaining': self.max_api_calls - self.api_calls_count,
            'usage_percentage': (self.api_calls_count / self.max_api_calls) * 100
        }
    
    # Keep all existing methods unchanged
    def _get_channel_average_views(self, channel_id):
        """Get channel average views (with caching) - UNCHANGED"""
        # Check cache first
        cached_channel = self.database.get_cached_channel_data(channel_id)
        if cached_channel and 'average_views' in cached_channel:
            return cached_channel['average_views']
        
        # Calculate from YouTube API
        print(f"📊 Calculating average views for channel: {channel_id}")
        average_views = self.youtube_service.calculate_channel_average_views(channel_id)
        self.api_calls_count += 1
        
        # Get additional channel info
        channel_info = self.youtube_service.get_channel_info(channel_id)
        if channel_info:
            self.api_calls_count += 1
            channel_data = {
                'average_views': average_views,
                'subscriber_count': channel_info['subscriber_count'],
                'video_count': channel_info['video_count'],
                'view_count': channel_info['view_count'],
                'title': channel_info['title']
            }
            
            # Cache the result
            self.database.cache_channel_data(channel_id, channel_data)
        
        return average_views
    
    def _passes_filters(self, video, filters):
        """Check if video passes all filters - UNCHANGED"""
        # Multiplier filter
        min_multiplier = filters.get('min_multiplier', 1.0)
        max_multiplier = filters.get('max_multiplier', 500.0)
        if not (min_multiplier <= video['multiplier'] <= max_multiplier):
            return False
        
        # Views filter
        min_views = filters.get('min_views', 0)
        max_views = filters.get('max_views', float('inf'))
        if not (min_views <= video['views'] <= max_views):
            return False
        
        # Duration filter (in seconds)
        min_duration = filters.get('min_duration_seconds', 0)
        max_duration = filters.get('max_duration_seconds', float('inf'))
        if not (min_duration <= video['duration_seconds'] <= max_duration):
            return False
        
        # Channel subscribers filter
        min_subscribers = filters.get('min_subscribers')
        max_subscribers = filters.get('max_subscribers')
        if min_subscribers is not None or max_subscribers is not None:
            channel_data = self.database.get_cached_channel_data(video['channel_id'])
            if channel_data and 'subscriber_count' in channel_data:
                subscriber_count = channel_data['subscriber_count']
                if min_subscribers is not None and subscriber_count < min_subscribers:
                    return False
                if max_subscribers is not None and subscriber_count > max_subscribers:
                    return False
        
        return True
    
    def get_search_statistics(self):
        """Get search statistics and popular queries - UNCHANGED"""
        return {
            'popular_searches': self.database.get_popular_searches(),
            'total_searches': self.database.searches_collection.count_documents({})
        }
    
    def format_number(self, num):
        """Format large numbers for display - UNCHANGED"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)