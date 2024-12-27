# src/api/app.py

import os
import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from . import routes
from . import slack_handler

# configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# initialize FastAPI app
app = FastAPI(
    title="Document Search Service",
    description="API for semantic search with Slack integration",
    version="1.0.0"
)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """run startup tasks"""
    try:
        logger.info("starting application...")
        
        # log non-sensitive environment variables
        env_vars = {
            "PROJECT_ID": os.getenv("PROJECT_ID"),
            "BUCKET_NAME": os.getenv("BUCKET_NAME"),
            "PORT": os.getenv("PORT"),
            "LOCATION": os.getenv("LOCATION")
        }
        logger.info("environment variables: %s", {k: v for k, v in env_vars.items() if v is not None})
        
        # check required environment variables
        required_vars = ["PROJECT_ID", "BUCKET_NAME", "SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"missing required environment variables: {', '.join(missing_vars)}")
        
        # include routers
        logger.info("including routers...")
        app.include_router(routes.router, tags=["Search"])
        app.include_router(slack_handler.router, tags=["Slack"])
        
        logger.info("application startup complete")
        
    except Exception as e:
        logger.error("error during startup: %s", str(e), exc_info=True)
        raise

@app.get("/health")
async def health_check():
    """health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "env": os.getenv("ENV", "production")
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info("starting uvicorn server on port %d", port)
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
