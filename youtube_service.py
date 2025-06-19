# import time
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
# from config import Config

# class YouTubeService:
#     def __init__(self):
#         self.youtube = build('youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
    
#     def search_videos(self, query, max_results=50):
#         """Search for videos based on query"""
#         try:
#             request = self.youtube.search().list(
#                 q=query,
#                 part='id,snippet',
#                 type='video',
#                 maxResults=max_results,
#                 order='relevance'
#             )
#             response = request.execute()
            
#             videos = []
#             for item in response['items']:
#                 video_data = {
#                     'video_id': item['id']['videoId'],
#                     'title': item['snippet']['title'],
#                     'channel_id': item['snippet']['channelId'],
#                     'channel_title': item['snippet']['channelTitle'],
#                     'published_at': item['snippet']['publishedAt']
#                 }
#                 videos.append(video_data)
            
#             return videos
#         except HttpError as e:
#             print(f"YouTube API error in search_videos: {e}")
#             return []
    
#     def get_video_stats(self, video_ids):
#         """Get detailed statistics for videos"""
#         try:
#             # YouTube API accepts max 50 video IDs per request
#             video_stats = {}
            
#             for i in range(0, len(video_ids), 50):
#                 batch_ids = video_ids[i:i+50]
#                 request = self.youtube.videos().list(
#                     part='statistics,contentDetails,status',
#                     id=','.join(batch_ids)
#                 )
#                 response = request.execute()
                
#                 for item in response['items']:
#                     # Skip private/unlisted videos
#                     if item['status']['privacyStatus'] not in ['public']:
#                         continue
                        
#                     video_id = item['id']
#                     stats = item['statistics']
#                     content_details = item['contentDetails']
                    
#                     video_stats[video_id] = {
#                         'views': int(stats.get('viewCount', 0)),
#                         'likes': int(stats.get('likeCount', 0)),
#                         'comments': int(stats.get('commentCount', 0)),
#                         'duration': content_details.get('duration', ''),
#                         'privacy_status': item['status']['privacyStatus']
#                     }
                
#                 time.sleep(Config.REQUEST_DELAY)
            
#             return video_stats
#         except HttpError as e:
#             print(f"YouTube API error in get_video_stats: {e}")
#             return {}
    
#     def get_channel_info(self, channel_id):
#         """Get channel information including subscriber count"""
#         try:
#             request = self.youtube.channels().list(
#                 part='statistics,snippet',
#                 id=channel_id
#             )
#             response = request.execute()
            
#             if response['items']:
#                 channel = response['items'][0]
#                 return {
#                     'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
#                     'video_count': int(channel['statistics'].get('videoCount', 0)),
#                     'view_count': int(channel['statistics'].get('viewCount', 0)),
#                     'title': channel['snippet']['title']
#                 }
#             return None
#         except HttpError as e:
#             print(f"YouTube API error in get_channel_info: {e}")
#             return None
    
#     def get_channel_videos(self, channel_id, max_results=500):
#         """Get all videos from a channel"""
#         try:
#             videos = []
#             next_page_token = None
            
#             while len(videos) < max_results:
#                 request = self.youtube.search().list(
#                     channelId=channel_id,
#                     part='id,snippet',
#                     type='video',
#                     maxResults=min(50, max_results - len(videos)),
#                     pageToken=next_page_token,
#                     order='date'
#                 )
#                 response = request.execute()
                
#                 for item in response['items']:
#                     video_id = item['id']['videoId']
#                     videos.append(video_id)
                
#                 next_page_token = response.get('nextPageToken')
#                 if not next_page_token:
#                     break
                
#                 time.sleep(Config.REQUEST_DELAY)
            
#             return videos
#         except HttpError as e:
#             print(f"YouTube API error in get_channel_videos: {e}")
#             return []
    
#     def calculate_channel_average_views(self, channel_id):
#         """Calculate average views per video for a channel"""
#         try:
#             # Get channel info first
#             channel_info = self.get_channel_info(channel_id)
#             if not channel_info or channel_info['video_count'] == 0:
#                 return 0
            
#             # For efficiency, use total channel views / video count
#             # This is faster than fetching all individual videos
#             average_views = channel_info['view_count'] / channel_info['video_count']
#             return int(average_views)
            
#         except Exception as e:
#             print(f"Error calculating channel average views: {e}")
#             return 0
    
#     def parse_duration(self, duration):
#         """Parse ISO 8601 duration to seconds"""
#         import re
        
#         pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
#         match = re.match(pattern, duration)
        
#         if not match:
#             return 0
        
#         hours = int(match.group(1) or 0)
#         minutes = int(match.group(2) or 0)
#         seconds = int(match.group(3) or 0)
        
#         return hours * 3600 + minutes * 60 + seconds

import time
import socket
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config

class YouTubeService:
    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
    
    def search_videos(self, query, max_results=50, region_code=None, language=None, order='relevance'):
        """Enhanced search for videos with global parameters"""
        try:
            search_params = {
                'q': query,
                'part': 'id,snippet',
                'type': 'video',
                'maxResults': max_results,
                'order': order
            }
            
            if region_code:
                search_params['regionCode'] = region_code
            if language:
                search_params['relevanceLanguage'] = language
            
            request = self.youtube.search().list(**search_params)
            response = request.execute()
            
            videos = []
            for item in response['items']:
                video_data = {
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'description': item['snippet'].get('description', '')[:200],
                    'thumbnail_url': item['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                    'region_code': region_code,
                    'language': language
                }
                videos.append(video_data)
            
            return videos
        except HttpError as e:
            print(f"YouTube API error in search_videos: {e}")
            return []
        except socket.gaierror as e:
            print(f"Network error in search_videos: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in search_videos: {e}")
            return []
    
    def search_trending_videos(self, region_code='US', category_id=None, max_results=50):
        """Get trending videos from specific region"""
        try:
            search_params = {
                'part': 'id,snippet,statistics',
                'chart': 'mostPopular',
                'regionCode': region_code,
                'maxResults': max_results
            }
            
            if category_id:
                search_params['videoCategoryId'] = category_id
            
            request = self.youtube.videos().list(**search_params)
            response = request.execute()
            
            videos = []
            for item in response['items']:
                video_data = {
                    'video_id': item['id'],
                    'title': item['snippet']['title'],
                    'channel_id': item['snippet']['channelId'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'views': int(item['statistics'].get('viewCount', 0)),
                    'likes': int(item['statistics'].get('likeCount', 0)),
                    'comments': int(item['statistics'].get('commentCount', 0)),
                    'region_code': region_code
                }
                videos.append(video_data)
            
            return videos
        except HttpError as e:
            print(f"YouTube API error in search_trending_videos: {e}")
            return []
        except socket.gaierror as e:
            print(f"Network error in search_trending_videos: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in search_trending_videos: {e}")
            return []
    
    def get_video_stats(self, video_ids):
        """Get detailed statistics for videos - ENHANCED"""
        try:
            video_stats = {}
            
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                request = self.youtube.videos().list(
                    part='statistics,contentDetails,status,snippet',
                    id=','.join(batch_ids)
                )
                response = request.execute()
                
                for item in response['items']:
                    if item['status']['privacyStatus'] not in ['public']:
                        continue
                        
                    video_id = item['id']
                    stats = item['statistics']
                    content_details = item['contentDetails']
                    snippet = item['snippet']
                    
                    video_stats[video_id] = {
                        'views': int(stats.get('viewCount', 0)),
                        'likes': int(stats.get('likeCount', 0)),
                        'comments': int(stats.get('commentCount', 0)),
                        'duration': content_details.get('duration', ''),
                        'privacy_status': item['status']['privacyStatus'],
                        'category_id': snippet.get('categoryId', ''),
                        'default_language': snippet.get('defaultLanguage', ''),
                        'tags': snippet.get('tags', [])[:10],
                        'live_broadcast_content': snippet.get('liveBroadcastContent', ''),
                        'definition': content_details.get('definition', ''),
                        'dimension': content_details.get('dimension', '')
                    }
                
                time.sleep(Config.REQUEST_DELAY)
            
            return video_stats
        except HttpError as e:
            print(f"YouTube API error in get_video_stats: {e}")
            return {}
        except socket.gaierror as e:
            print(f"Network error in get_video_stats: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error in get_video_stats: {e}")
            return {}
    
    def get_channel_info(self, channel_id):
        """Get enhanced channel information"""
        try:
            request = self.youtube.channels().list(
                part='statistics,snippet,brandingSettings',
                id=channel_id
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                branding = channel.get('brandingSettings', {})
                
                return {
                    'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
                    'video_count': int(channel['statistics'].get('videoCount', 0)),
                    'view_count': int(channel['statistics'].get('viewCount', 0)),
                    'title': channel['snippet']['title'],
                    'description': channel['snippet'].get('description', '')[:300],
                    'country': channel['snippet'].get('country', ''),
                    'published_at': channel['snippet']['publishedAt'],
                    'thumbnail_url': channel['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                    'keywords': branding.get('channel', {}).get('keywords', '').split()[:10],
                    'default_language': branding.get('channel', {}).get('defaultLanguage', '')
                }
            return None
        except HttpError as e:
            print(f"YouTube API error in get_channel_info: {e}")
            return None
        except socket.gaierror as e:
            print(f"Network error in get_channel_info: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in get_channel_info: {e}")
            return None
    
    def get_video_categories(self, region_code='US'):
        """Get video categories for a specific region"""
        try:
            request = self.youtube.videoCategories().list(
                part='snippet',
                regionCode=region_code
            )
            response = request.execute()
            
            categories = {}
            for item in response['items']:
                categories[item['id']] = item['snippet']['title']
            
            return categories
        except HttpError as e:
            print(f"YouTube API error in get_video_categories: {e}")
            return {}
        except socket.gaierror as e:
            print(f"Network error in get_video_categories: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error in get_video_categories: {e}")
            return {}
    
    def search_channels(self, query, max_results=25, region_code=None):
        """Search for channels related to query"""
        try:
            search_params = {
                'q': query,
                'part': 'id,snippet',
                'type': 'channel',
                'maxResults': max_results,
                'order': 'relevance'
            }
            
            if region_code:
                search_params['regionCode'] = region_code
            
            request = self.youtube.search().list(**search_params)
            response = request.execute()
            
            channels = []
            for item in response['items']:
                channel_data = {
                    'channel_id': item['id']['channelId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet'].get('description', '')[:200],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail_url': item['snippet']['thumbnails'].get('medium', {}).get('url', ''),
                    'region_code': region_code
                }
                channels.append(channel_data)
            
            return channels
        except HttpError as e:
            print(f"YouTube API error in search_channels: {e}")
            return []
        except socket.gaierror as e:
            print(f"Network error in search_channels: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in search_channels: {e}")
            return []
    
    def get_channel_videos(self, channel_id, max_results=500):
        """Get all videos from a channel - UNCHANGED"""
        try:
            videos = []
            next_page_token = None
            
            while len(videos) < max_results:
                request = self.youtube.search().list(
                    channelId=channel_id,
                    part='id,snippet',
                    type='video',
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token,
                    order='date'
                )
                response = request.execute()
                
                for item in response['items']:
                    video_id = item['id']['videoId']
                    videos.append(video_id)
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                
                time.sleep(Config.REQUEST_DELAY)
            
            return videos
        except HttpError as e:
            print(f"YouTube API error in get_channel_videos: {e}")
            return []
        except socket.gaierror as e:
            print(f"Network error in get_channel_videos: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in get_channel_videos: {e}")
            return []
    
    def calculate_channel_average_views(self, channel_id):
        """Calculate average views per video for a channel - UNCHANGED"""
        try:
            channel_info = self.get_channel_info(channel_id)
            if not channel_info or channel_info['video_count'] == 0:
                return 0
            
            average_views = channel_info['view_count'] / channel_info['video_count']
            return int(average_views)
            
        except Exception as e:
            print(f"Error calculating channel average views: {e}")
            return 0
    
    def parse_duration(self, duration):
        """Parse ISO 8601 duration to seconds - UNCHANGED"""
        import re
        
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds