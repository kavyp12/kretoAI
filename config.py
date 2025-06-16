# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # Add this line
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    MONGO_URI = os.getenv('MONGO_URI')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'youtube_outliers')
    SECRET_KEY = os.getenv('SECRET_KEY')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    MAX_RESULTS_PER_SEARCH = 50
    MAX_VIDEOS_PER_CHANNEL = 500
    REQUEST_DELAY = 0.5

# # config.py
# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Config:
#     # Removed GEMINI_API_KEY as it's not used in the current code
#     MONGO_URI = os.getenv('MONGO_URI')
#     MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'youtube_outliers')
#     SECRET_KEY = os.getenv('SECRET_KEY')
#     FLASK_ENV = os.getenv('FLASK_ENV', 'development')
#     DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
#     # Web Scraping Configuration - Enhanced
#     USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
#     MAX_RESULTS_PER_SEARCH = 50
#     MAX_VIDEOS_PER_CHANNEL = 500
#     REQUEST_DELAY = 0.5
    
#     # Scraping specific settings
#     SCRAPING_TIMEOUT = 10
#     SCRAPING_RETRIES = 3
#     MAX_CONCURRENT_REQUESTS = 5