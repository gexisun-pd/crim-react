#!/usr/bin/env python3

import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS

# Add the core directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from routes.pieces import pieces_bp

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for React frontend with comprehensive configuration
    CORS(app, 
         origins="*",  # Allow all origins for development
         supports_credentials=False,  # Set to False when using origins="*"
         allow_headers=['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         max_age=3600  # Cache preflight requests for 1 hour
    )
    
    # Add custom CORS headers for better compatibility
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept,Origin,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'false')
        return response
    
    # Register blueprints
    app.register_blueprint(pieces_bp, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return jsonify({"status": "healthy", "service": "pieces-api"})
    
    # Root endpoint
    @app.route('/')
    def root():
        return jsonify({
            "message": "Pieces Analysis API",
            "version": "1.0.0",
            "endpoints": [
                "/api/pieces",
                "/api/pieces/<int:piece_id>",
                "/api/note-sets",
                "/health"
            ]
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=9000)
