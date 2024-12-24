# src/api/app.py

import os
import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from . import routes
from . import slack_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Vector Search Service",
    description="API for semantic search with Slack integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    try:
        logger.info("Starting application...")
        
        # Log non-sensitive environment variables
        env_vars = {
            "PROJECT_ID": os.getenv("PROJECT_ID"),
            "BUCKET_NAME": os.getenv("BUCKET_NAME"),
            "PORT": os.getenv("PORT"),
            "LOCATION": os.getenv("LOCATION")
        }
        logger.info("Environment variables: %s", {k: v for k, v in env_vars.items() if v is not None})
        
        # Check required environment variables
        required_vars = ["PROJECT_ID", "BUCKET_NAME", "SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Include routers
        logger.info("Including routers...")
        app.include_router(routes.router, tags=["Search"])
        app.include_router(slack_handler.router, tags=["Slack"])
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error("Error during startup: %s", str(e), exc_info=True)
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "env": os.getenv("ENV", "production")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info("Starting uvicorn server on port %d", port)
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
