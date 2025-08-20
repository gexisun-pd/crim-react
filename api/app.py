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
    
    # Enable CORS for React frontend - 使用Flask-CORS扩展统一处理
    CORS(app, 
         origins="*",  # Allow all origins for development
         supports_credentials=False,  # Set to False when using origins="*"
         allow_headers=['Content-Type', 'Authorization', 'Accept', 'Origin', 'X-Requested-With'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         max_age=3600  # Cache preflight requests for 1 hour
    )
    
    # 移除手动的CORS头设置以避免冲突
    # Flask-CORS扩展已经处理了所有CORS头设置
    
    # Register blueprints - 移除/api前缀，让nginx处理路径重写
    app.register_blueprint(pieces_bp)
    
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
                "/pieces",
                "/pieces/<int:piece_id>",
                "/pieces/<int:piece_id>/notes", 
                "/pieces/<int:piece_id>/musicxml",
                "/note-sets",
                "/health"
            ]
        })
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=9000)
