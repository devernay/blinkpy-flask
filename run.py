#!/usr/bin/env python3
"""Run the Blink Flask application."""

import sys
import os
import argparse

# Add the blinkpy directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'blinkpy'))

def main():
    parser = argparse.ArgumentParser(description='Blink Camera Flask Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--cache', default='cache', help='Cache directory for credentials, thumbnails, and clips (default: cache)')
    
    args = parser.parse_args()
    
    # Import app only after parsing args to avoid side effects during help
    from app import app
    
    # Set cache directory in app
    app.config['CACHE_DIR'] = args.cache
    
    app.run(debug=args.debug, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
