# from flask import Flask, render_template, request, jsonify
# from flask_cors import CORS
# from outlier_detector import OutlierDetector
# from config import Config
# import traceback

# app = Flask(__name__)
# app.config.from_object(Config)
# CORS(app)

# # Initialize outlier detector
# outlier_detector = OutlierDetector()

# @app.route('/')
# def index():
#     """Render the main page"""
#     return render_template('index.html')

# @app.route('/api/search', methods=['POST'])
# def search_outliers():
#     """API endpoint to search for outlier videos"""
#     try:
#         data = request.get_json()
        
#         if not data or 'query' not in data:
#             return jsonify({'error': 'Query parameter is required'}), 400
        
#         query = data['query'].strip()
#         if not query:
#             return jsonify({'error': 'Query cannot be empty'}), 400
        
#         # Extract filters
#         filters = {}
        
#         # Multiplier filter
#         if 'min_multiplier' in data:
#             filters['min_multiplier'] = float(data['min_multiplier'])
#         if 'max_multiplier' in data:
#             filters['max_multiplier'] = float(data['max_multiplier'])
        
#         # Views filter
#         if 'min_views' in data:
#             filters['min_views'] = int(data['min_views'])
#         if 'max_views' in data:
#             filters['max_views'] = int(data['max_views'])
        
#         # Duration filter (convert minutes to seconds)
#         if 'min_duration_minutes' in data:
#             filters['min_duration_seconds'] = int(data['min_duration_minutes']) * 60
#         if 'max_duration_minutes' in data:
#             filters['max_duration_seconds'] = int(data['max_duration_minutes']) * 60
        
#         # Subscribers filter
#         if 'min_subscribers' in data:
#             filters['min_subscribers'] = int(data['min_subscribers'])
#         if 'max_subscribers' in data:
#             filters['max_subscribers'] = int(data['max_subscribers'])
        
#         # Detect outliers
#         outliers = outlier_detector.detect_outliers(query, filters)
        
#         # Format response
#         formatted_outliers = []
#         for video in outliers:
#             formatted_video = {
#                 'video_id': video['video_id'],
#                 'title': video['title'],
#                 'channel_title': video['channel_title'],
#                 'views': video['views'],
#                 'views_formatted': outlier_detector.format_number(video['views']),
#                 'channel_avg_views': video['channel_avg_views'],
#                 'channel_avg_views_formatted': outlier_detector.format_number(video['channel_avg_views']),
#                 'multiplier': video['multiplier'],
#                 'likes': video['likes'],
#                 'likes_formatted': outlier_detector.format_number(video['likes']),
#                 'comments': video['comments'],
#                 'comments_formatted': outlier_detector.format_number(video['comments']),
#                 'duration': video['duration'],
#                 'duration_seconds': video['duration_seconds'],
#                 'url': video['url'],
#                 'published_at': video['published_at']
#             }
#             formatted_outliers.append(formatted_video)
        
#         return jsonify({
#             'success': True,
#             'query': query,
#             'total_results': len(formatted_outliers),
#             'outliers': formatted_outliers,
#             'filters_applied': filters
#         })
    
#     except Exception as e:
#         print(f"Error in search_outliers: {str(e)}")
#         print(traceback.format_exc())
#         return jsonify({
#             'success': False,
#             'error': f'An error occurred: {str(e)}'
#         }), 500

# @app.route('/api/stats', methods=['GET'])
# def get_stats():
#     """Get search statistics"""
#     try:
#         stats = outlier_detector.get_search_statistics()
#         return jsonify({
#             'success': True,
#             'stats': stats
#         })
#     except Exception as e:
#         print(f"Error in get_stats: {str(e)}")
#         return jsonify({
#             'success': False,
#             'error': f'An error occurred: {str(e)}'
#         }), 500

# @app.route('/api/health', methods=['GET'])
# def health_check():
#     """Health check endpoint"""
#     return jsonify({
#         'status': 'healthy',
#         'service': 'YouTube Outlier Detection Tool'
#     })

# @app.errorhandler(404)
# def not_found(error):
#     return jsonify({'error': 'Endpoint not found'}), 404

# @app.errorhandler(500)
# def internal_error(error):
#     return jsonify({'error': 'Internal server error'}), 500

# if __name__ == '__main__':
#     app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)


from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from outlier_detector import OutlierDetector
from config import Config
import traceback

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize outlier detector
outlier_detector = OutlierDetector()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_outliers():
    """API endpoint to search for outlier videos"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Query cannot be empty'}), 400
        
        # Extract filters from the 'filters' object in the request
        filters = data.get('filters', {})

        # Detect outliers
        outliers = outlier_detector.detect_outliers(query, filters)
        
        # Format response - now includes all advanced metrics
        formatted_outliers = []
        for video in outliers:
            formatted_video = {
                'video_id': video['video_id'],
                'title': video['title'],
                'channel_title': video['channel_title'],
                'views': video['views'],
                'views_formatted': outlier_detector.format_number(video['views']),
                'channel_avg_views': video['channel_avg_views'],
                'channel_avg_views_formatted': outlier_detector.format_number(video['channel_avg_views']),
                'multiplier': video['multiplier'],
                'likes': video['likes'],
                'likes_formatted': outlier_detector.format_number(video['likes']),
                'comments': video['comments'],
                'comments_formatted': outlier_detector.format_number(video['comments']),
                'duration': video['duration'],
                'duration_seconds': video['duration_seconds'],
                'url': video['url'],
                'published_at': video['published_at'],
                # --- New Advanced Fields ---
                'rank': video.get('rank'),
                'performance_tier': video.get('performance_tier'),
                'composite_score': video.get('composite_score'),
                'viral_score': video.get('viral_score'),
                'engagement_rate': video.get('engagement_rate'),
                'relevance_score': video.get('relevance_score'),
                'video_age_days': video.get('video_age_days')
            }
            formatted_outliers.append(formatted_video)
        
        return jsonify({
            'success': True,
            'query': query,
            'total_results': len(formatted_outliers),
            'outliers': formatted_outliers,
            'filters_applied': filters
        })
    
    except Exception as e:
        print(f"Error in search_outliers: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get search statistics"""
    try:
        stats = outlier_detector.get_search_statistics()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"Error in get_stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'YouTube Outlier Detection Tool'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)