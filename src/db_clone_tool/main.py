"""
MySQL Schema Clone Tool - Flask Application Entry Point
"""
import logging
from flask import Flask
from src.db_clone_tool.routes.web import web_bp
from src.db_clone_tool.routes.api import api_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure Flask application"""
    from pathlib import Path
    
    # Get the directory where this file is located
    base_dir = Path(__file__).parent
    
    app = Flask(
        __name__,
        template_folder=str(base_dir / 'templates'),
        static_folder=str(base_dir / 'static'),
        static_url_path='/static'
    )
    
    # Register blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    
    return app


def run_app(host='0.0.0.0', port=5000, debug=True):
    """Run the Flask application"""
    app = create_app()
    
    print("\n" + "="*70)
    print("  MySQL SCHEMA CLONE TOOL")
    print("="*70)
    print(f"  Service: Web API & UI")
    print(f"  Port: {port}")
    print(f"  Debug Mode: {'ENABLED' if debug else 'DISABLED'}")
    print(f"  Endpoints:")
    print(f"    - GET  /                    : Web UI")
    print(f"    - GET  /api/connections      : List connections")
    print(f"    - POST /api/connections       : Add connection")
    print(f"    - POST /api/connections/test  : Test connection")
    print(f"    - DELETE /api/connections/<id>: Delete connection")
    print(f"    - GET  /api/schemas/<id>     : List schemas")
    print(f"    - POST /api/clone             : Start clone job")
    print(f"    - GET  /api/clone/status/<id> : Get clone status")
    print(f"    - GET  /api/clone/logs/<id>  : Get clone logs")
    print("="*70 + "\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app(port=5000, debug=True)
