#!/usr/bin/env python3
"""
YouTube Outlier Detection Tool - Runner Script
Handles both development and production environments
"""

import os
import sys
from app import app
from config import Config
from database import Database

def setup_environment():
    """Setup environment and check requirements"""
    print("🚀 Starting YouTube Outlier Detection Tool...")
    
    # Check if required environment variables are set
    required_vars = ['YOUTUBE_API_KEY', 'MONGO_URI']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    print("✅ Environment variables verified")
    
    # Test database connection
    try:
        db = Database()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your MongoDB connection string.")
        sys.exit(1)
    
    print("🎯 Ready to detect YouTube outliers!")

def main():
    """Main function to run the application"""
    setup_environment()
    
    # Run the Flask app
    if Config.FLASK_ENV == 'development':
        # Development mode with auto-reload
        app.run(
            debug=Config.DEBUG,
            host='0.0.0.0',
            port=5000,
            use_reloader=True
        )
    else:
        # Production mode
        app.run(
            debug=False,
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000))
        )

if __name__ == '__main__':
    main()