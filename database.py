from pymongo import MongoClient
from datetime import datetime, timedelta
from config import Config

class Database:
    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI)
        self.db = self.client[Config.MONGODB_DB_NAME]
        self.videos_collection = self.db.videos
        self.channels_collection = self.db.channels
        self.searches_collection = self.db.searches
        
        # Create indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better query performance"""
        try:
            self.videos_collection.create_index("video_id", unique=True)
            self.videos_collection.create_index("channel_id")
            self.videos_collection.create_index("search_query")
            self.channels_collection.create_index("channel_id", unique=True)
            self.searches_collection.create_index("query")
            self.searches_collection.create_index("timestamp")
        except Exception as e:
            print(f"Error creating indexes: {e}")
    
    def cache_video_data(self, video_data, search_query):
        """Cache video data in database"""
        try:
            video_data['search_query'] = search_query
            video_data['cached_at'] = datetime.utcnow()
            
            self.videos_collection.update_one(
                {'video_id': video_data['video_id']},
                {'$set': video_data},
                upsert=True
            )
        except Exception as e:
            print(f"Error caching video data: {e}")
    
    def cache_channel_data(self, channel_id, channel_data):
        """Cache channel data in database"""
        try:
            channel_data['channel_id'] = channel_id
            channel_data['cached_at'] = datetime.utcnow()
            
            self.channels_collection.update_one(
                {'channel_id': channel_id},
                {'$set': channel_data},
                upsert=True
            )
        except Exception as e:
            print(f"Error caching channel data: {e}")
    
    def get_cached_channel_data(self, channel_id, max_age_hours=24):
        """Get cached channel data if not expired"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            cached_data = self.channels_collection.find_one({
                'channel_id': channel_id,
                'cached_at': {'$gte': cutoff_time}
            })
            
            return cached_data
        except Exception as e:
            print(f"Error getting cached channel data: {e}")
            return None
    
    def get_cached_search_results(self, query, max_age_hours=6):
        """Get cached search results if not expired"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            cached_videos = list(self.videos_collection.find({
                'search_query': query,
                'cached_at': {'$gte': cutoff_time}
            }))
            
            return cached_videos
        except Exception as e:
            print(f"Error getting cached search results: {e}")
            return []
    
    def save_search_history(self, query, results_count, filters=None):
        """Save search history for analytics"""
        try:
            search_record = {
                'query': query,
                'results_count': results_count,
                'filters': filters or {},
                'timestamp': datetime.utcnow()
            }
            
            self.searches_collection.insert_one(search_record)
        except Exception as e:
            print(f"Error saving search history: {e}")
    
    def get_popular_searches(self, limit=10):
        """Get most popular search queries"""
        try:
            pipeline = [
                {'$group': {
                    '_id': '$query',
                    'count': {'$sum': 1},
                    'last_searched': {'$max': '$timestamp'}
                }},
                {'$sort': {'count': -1}},
                {'$limit': limit}
            ]
            
            results = list(self.searches_collection.aggregate(pipeline))
            return results
        except Exception as e:
            print(f"Error getting popular searches: {e}")
            return []
    
    def cleanup_old_data(self, days_old=30):
        """Clean up old cached data"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean old videos
            result1 = self.videos_collection.delete_many({
                'cached_at': {'$lt': cutoff_time}
            })
            
            # Clean old channels
            result2 = self.channels_collection.delete_many({
                'cached_at': {'$lt': cutoff_time}
            })
            
            # Clean old searches
            result3 = self.searches_collection.delete_many({
                'timestamp': {'$lt': cutoff_time}
            })
            
            print(f"Cleaned up {result1.deleted_count} videos, {result2.deleted_count} channels, {result3.deleted_count} searches")
            
        except Exception as e:
            print(f"Error cleaning up old data: {e}")