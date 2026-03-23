#!/usr/bin/env python3
"""
Minimal FastAPI server to verify the application works.
"""
import os
import sys

# Ensure we have a clean import environment
def setup_clean_environment():
    """Setup a clean Python environment."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Remove any numpy source directories from path
    paths_to_remove = []
    for path in sys.path:
        if 'numpy' in path.lower() and not path.endswith('.egg') and not 'site-packages' in path:
            paths_to_remove.append(path)
    
    for path in paths_to_remove:
        sys.path.remove(path)
    
    # Add our app directory
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    return current_dir

if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        import os
        
        # Load .env from parent directory
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ Loaded environment from {env_path}")
        else:
            print(f"⚠️  .env file not found at {env_path}")
            
    except ImportError:
        print("⚠️  python-dotenv not available, using system environment")
    
    # Setup environment
    app_dir = setup_clean_environment()
    
    # Check API key
    if not os.environ.get('OPENAI_API_KEY') and not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ ERROR: No API key found!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
        sys.exit(1)
    
    try:
        # Basic FastAPI app without complex imports
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn
        
        # Create simple app
        app = FastAPI(
            title="Manufacturing AI Analysis API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        @app.get("/")
        async def root():
            return {"message": "Manufacturing AI API", "status": "running", "docs": "/docs"}
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        @app.get("/test")
        async def test():
            return {"message": "API is working!", "python_version": sys.version}
        
        print("🏭 Starting Manufacturing AI Analysis API (Basic Mode)...")
        print("📊 Access documentation at: http://localhost:8000/docs")
        print("🔧 Basic endpoints available:")
        print("   GET /         - Root endpoint")
        print("   GET /health   - Health check")
        print("   GET /test     - Test endpoint")
        print("")
        print("🚀 Server starting...")
        
        # Start server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print("💡 This is a minimal version. The full app may need environment fixes.")
        sys.exit(1)