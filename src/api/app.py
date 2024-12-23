# src/api/app.py
import os
import logging
import sys
from fastapi import FastAPI
from . import routes
from . import slack_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vector Search Service")

@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    try:
        logger.info("Starting application...")
        # Log environment variables (excluding sensitive ones)
        logger.info(f"PROJECT_ID: {os.getenv('PROJECT_ID')}")
        logger.info(f"BUCKET_NAME: {os.getenv('BUCKET_NAME')}")
        logger.info(f"PORT: {os.getenv('PORT')}")
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        # Include routers
        logger.info("Including routers...")
        app.include_router(routes.router)
        app.include_router(slack_handler.router)
        
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        raise

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting uvicorn server on port {port}")
    uvicorn.run(
        "src.api.app:app", 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    )