import os
import io
import base64
import logging
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import pdf2image
from PIL import Image
import google.generativeai as genai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/ping")
def health_check():
    return {"status": "ok"}


# Configure Google Gemini API
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("FATAL ERROR: GOOGLE_API_KEY not found in .env file.")
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
        poppler_path = os.getenv("POPPLER_PATH", None)  # Use .env variable, fallback to system path
        contents = uploaded_file.file.read()
        images = pdf2image.convert_from_bytes(contents, poppler_path=poppler_path)
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
        logger.error("Poppler not found. Make sure it's installed and POPPLER_PATH is set correctly.")
        raise Exception("Poppler not found or misconfigured.")
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
        'analysis': """You are an HR specializing in recruitment. Analyze the following job description and resume. Determine how well 
                       the resume matches the job requirements. Highlight the candidate's relevant strengths and experiences.""",
        'match': """You are a skilled ATS tracker you need to show how much percentage the job discription match to the resume ...""",
        'skills': """You are a career development analyst you need to gave the user what are the missing skills in the resume corresponding to the job discription..."""
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
        return JSONResponse(content={"error": str(e)}, status_code=500)
