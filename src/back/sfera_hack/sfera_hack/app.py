from fastapi import FastAPI

from sfera_hack.api.sfera.projects import router as projects_router
from sfera_hack.api.sfera.login import router as login_router


app = FastAPI(
    title="Sfera Hack API",
    description="A simple dummy FastAPI application",
    version="1.0.0",
)

# Include routers
app.include_router(projects_router)
app.include_router(login_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Sfera Hack API!", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "sfera-hack-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
