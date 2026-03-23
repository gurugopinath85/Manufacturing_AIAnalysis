#!/usr/bin/env python3
"""
Simple launcher for Manufacturing AI Analysis API
"""
import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set environment variables
os.environ.setdefault('PYTHONPATH', current_dir)

if __name__ == "__main__":
    try:
        import uvicorn
        
        # Basic validation
        if not os.environ.get('OPENAI_API_KEY') and not os.environ.get('ANTHROPIC_API_KEY'):
            print("❌ ERROR: No API key found!")
            print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
            sys.exit(1)
            
        print("🏭 Starting Manufacturing AI Analysis API...")
        print("📊 Access documentation at: http://localhost:8000/docs")
        print("🎯 API available at: http://localhost:8000/api/v1/")
        
        # Start the server
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)