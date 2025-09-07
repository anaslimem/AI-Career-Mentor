from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from cv_parser import extract_text_from_pdf
from agent import run_agent
import os
import traceback

app = FastAPI(title="AI Career Mentor API")

# Add CORS middleware to allow Streamlit to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Career Mentor API is running!"}

@app.post("/analyze")
async def analyze_cv(role: str = Form(...), cv: UploadFile = File(...)):
    try:
        if cv.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        pdf_bytes = await cv.read()
        cv_text = extract_text_from_pdf(pdf_bytes)

        if not cv_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        report = run_agent(cv_text,role)
        return {"report": report}

    except Exception as e:
        tb = traceback.format_exc()
        # temporary: return full traceback (or log it). Remove before production.
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}\n\nTraceback:\n{tb}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Changed default port to 8000
    print(f"🚀 Starting AI Career Mentor API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)