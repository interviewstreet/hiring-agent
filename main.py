import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.resume import router as resume_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Resume Agent API",
    description="file upload endpoint for resume evaluation",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(resume_router)


@app.get("/")
async def root():
    return {"message": "Resume Agent API is running", "docs": "/docs"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
