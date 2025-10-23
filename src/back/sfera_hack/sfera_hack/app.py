from fastapi import FastAPI


app = FastAPI(title="Sfera Hack API", description="A simple dummy FastAPI application", version="1.0.0")


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
