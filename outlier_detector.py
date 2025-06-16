from youtube_service import YouTubeService
from database import Database
import time

class OutlierDetector:
    def __init__(self):
        self.youtube_service = YouTubeService()
        self.database = Database()
    
    def detect_outliers(self, query, filters=None):
        """Main function to detect outlier videos"""
        if filters is None:
            filters = {}
        
        print(f"🔍 Searching for videos: {query}")
        
        # Step 1: Search for videos
        videos = self._get_videos_for_query(query)
        if not videos:
            return []
        
        print(f"📹 Found {len(videos)} videos")
        
        # Step 2: Get video statistics
        video_ids = [v['video_id'] for v in videos]
        video_stats = self.youtube_service.get_video_stats(video_ids)
        
        # Step 3: Calculate multipliers
        outlier_videos = []
        processed_channels = {}
        
        for video in videos:
            video_id = video['video_id']
            channel_id = video['channel_id']
            
            # Skip if video stats not available or video is private
            if video_id not in video_stats:
                continue
            
            video_views = video_stats[video_id]['views']
            
            # Get channel average views (with caching)
            if channel_id not in processed_channels:
                channel_avg = self._get_channel_average_views(channel_id)
                processed_channels[channel_id] = channel_avg
            else:
                channel_avg = processed_channels[channel_id]
            
            if channel_avg == 0:
                continue
            
            # Calculate multiplier
            multiplier = video_views / channel_avg
            
            # Create video result
            video_result = {
                'video_id': video_id,
                'title': video['title'],
                'channel_title': video['channel_title'],
                'channel_id': channel_id,
                'views': video_views,
                'channel_avg_views': channel_avg,
                'multiplier': round(multiplier, 2),
                'likes': video_stats[video_id]['likes'],
                'comments': video_stats[video_id]['comments'],
                'duration': video_stats[video_id]['duration'],
                'duration_seconds': self.youtube_service.parse_duration(video_stats[video_id]['duration']),
                'published_at': video['published_at'],
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
            # Apply filters
            if self._passes_filters(video_result, filters):
                outlier_videos.append(video_result)
        
        # Sort by multiplier descending
        outlier_videos.sort(key=lambda x: x['multiplier'], reverse=True)
        
        # Save search history
        self.database.save_search_history(query, len(outlier_videos), filters)
        
        print(f"🎯 Found {len(outlier_videos)} outlier videos")
        return outlier_videos
    
    def _get_videos_for_query(self, query):
        """Get videos for query (check cache first)"""
        # Check cache first
        cached_videos = self.database.get_cached_search_results(query)
        if cached_videos:
            print("📦 Using cached search results")
            return cached_videos
        
        # Search YouTube API
        videos = self.youtube_service.search_videos(query)
        
        # Cache the results
        for video in videos:
            self.database.cache_video_data(video, query)
        
        return videos
    
    def _get_channel_average_views(self, channel_id):
        """Get channel average views (with caching)"""
        # Check cache first
        cached_channel = self.database.get_cached_channel_data(channel_id)
        if cached_channel and 'average_views' in cached_channel:
            return cached_channel['average_views']
        
        # Calculate from YouTube API
        print(f"📊 Calculating average views for channel: {channel_id}")
        average_views = self.youtube_service.calculate_channel_average_views(channel_id)
        
        # Get additional channel info
        channel_info = self.youtube_service.get_channel_info(channel_id)
        if channel_info:
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
        """Check if video passes all filters"""
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
        
        # Channel subscribers filter (requires additional API call)
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
        """Get search statistics and popular queries"""
        return {
            'popular_searches': self.database.get_popular_searches(),
            'total_searches': self.database.searches_collection.count_documents({})
        }
    
    def format_number(self, num):
        """Format large numbers for display"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num) 

