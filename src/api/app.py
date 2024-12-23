# src/api/app.py

import os
import uvicorn
from fastapi import FastAPI
from . import routes
from . import slack_handler

app = FastAPI(title="Vector Search Service")

# Include routers
app.include_router(routes.router)
app.include_router(slack_handler.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def start():
    """Launched with `poetry run start` at root level"""
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    start()
