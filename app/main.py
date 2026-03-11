from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import db_manager
from app.core.responses.base import Response
from fastapi.exceptions import RequestValidationError
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Database Schema
try:
    db_manager.init_db()
except Exception as e:
    logger.error(f"Database initialization failed: {e}", exc_info=True)
    # Continue to allow app to start and report error via API

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_msg = f"Global exception: {str(exc)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    
    # Return structured error response
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "detail": str(exc), # Explicitly expose error detail for debugging
            "message": "服务器内部错误，请稍后重试",
            "data": None
        },
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code, 
            "detail": exc.detail, 
            "message": exc.detail,
            "data": None
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "detail": exc.errors(),
            "message": "请求参数验证失败",
            "data": None
        },
    )

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve Frontend Static Files
# In Docker/Production, we build the frontend and put it in /app/frontend/dist (as per Dockerfile)
# Or ./frontend/dist relative to app root?
# Dockerfile copies frontend/dist to /app/frontend/dist
# But WORKDIR is /app
# So path is ./frontend/dist
# Let's be robust
base_dir = os.path.dirname(os.path.abspath(__file__)) # /app/app
root_dir = os.path.dirname(base_dir) # /app
frontend_dist = os.path.join(root_dir, "frontend", "dist")

if not os.path.exists(frontend_dist):
    # Try alternate location if running locally not in docker
    frontend_dist = os.path.join(root_dir, "..", "frontend", "dist")

logger.info(f"Frontend dist path: {frontend_dist}, exists: {os.path.exists(frontend_dist)}")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API requests are handled by router above (order matters? No, this is catch-all)
        # But include_router is already added.
        if full_path.startswith("api"):
             return JSONResponse(status_code=404, content={"detail": "API endpoint not found"})
        
        # Check if file exists (e.g. favicon.ico)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to index.html for client-side routing
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

@app.get("/")
def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to MADF API. Frontend not found.", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
