import os
import io
import base64
import logging
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pdf2image
from PIL import Image
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Serve the main HTML file at root
@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/ping")
def health_check():
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "AI Resume Analyzer"}

# Configure Google Gemini API
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("FATAL ERROR: GOOGLE_API_KEY not found in environment variables.")
    else:
        genai.configure(api_key=api_key)
        logger.info("Google Generative AI configured successfully.")
except Exception as e:
    logger.error(f"Error configuring Google API: {e}")

# --- Helper Functions ---
def get_gemini_response(input_text, pdf_image_content):
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content([input_text, pdf_image_content[0]])
        return response.text
    except Exception as e:
        logger.error(f"Error during Gemini API call: {e}")
        raise Exception("AI model communication failed. Check API key or service availability.")

def setup_pdf_image(uploaded_file):
    try:
        # Reset file pointer to beginning and read the uploaded file content
        uploaded_file.file.seek(0)
        contents = uploaded_file.file.read()
        
        # Convert PDF to images (poppler is installed via apt-get in Docker)
        images = pdf2image.convert_from_bytes(contents)
        first_page = images[0]

        img_byte_arr = io.BytesIO()
        first_page.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

        pdf_parts = [{
            "mime_type": "image/jpeg",
            "data": base64.b64encode(img_byte_arr).decode()
        }]
        return pdf_parts
    except pdf2image.exceptions.PDFInfoNotInstalledError:
        logger.error("Poppler not found. Make sure it's installed.")
        raise Exception("PDF processing tools not available.")
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        raise Exception(f"PDF processing error: {e}")

# --- Routes ---

@app.post("/analyze")
async def analyze_resume_endpoint(
    resume: UploadFile = File(...),
    jobDescription: str = Form(...),
    promptType: str = Form(default="analysis")
):
    logger.info("Received request for /analyze")

    if not jobDescription.strip():
        return JSONResponse(content={"error": "Job description cannot be empty."}, status_code=400)

    prompts = {
        'analysis': """You are an HR specialist specializing in recruitment. Analyze the following job description and resume. Determine how well 
                       the resume matches the job requirements. Highlight the candidate's relevant strengths and experiences.""",
        'match': """You are a skilled ATS tracker. You need to show how much percentage the job description matches the resume.""",
        'skills': """You are a career development analyst. You need to give the user what are the missing skills in the resume corresponding to the job description."""
    }

    base_prompt = prompts.get(promptType)
    if not base_prompt:
        return JSONResponse(content={"error": "Invalid analysis type specified."}, status_code=400)

    input_text = f"**JOB DESCRIPTION:**\n{jobDescription.strip()}\n\n**TASK:**\n{base_prompt}"

    try:
        pdf_content = setup_pdf_image(resume)
        response_text = get_gemini_response(input_text, pdf_content)
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# For Railway deployment - start server if run directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
