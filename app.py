import os
import base64
import io
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import pdf2image
from PIL import Image
import google.generativeai as genai

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- AI Configuration ---
# Securely configure the Google Generative AI client
try:
    api_key = os.getenv("GOOGLE_API_KEY") 
    if not api_key:
        app.logger.error("FATAL ERROR: GOOGLE_API_KEY not found in .env file.")
    else:
        genai.configure(api_key=api_key)
        app.logger.info("Google Generative AI configured successfully.")
except Exception as e:
    app.logger.error(f"Error configuring Google API: {e}")

def get_gemini_response(input_text, pdf_image_content):
    """Generates content using the Gemini model."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content([input_text, pdf_image_content[0]])
        return response.text
    except Exception as e:
        app.logger.error(f"Error during Gemini API call: {e}")
        raise Exception("Failed to communicate with the AI model. The API key might be invalid or the service is temporarily unavailable.")

def setup_pdf_image(uploaded_file):
    """Converts the first page of a PDF to a format suitable for the AI model."""
    if not uploaded_file or uploaded_file.filename == '':
        raise FileNotFoundError("No file was uploaded.")
    
    try:
        # ✅ THIS IS THE CORRECTED LINE
        poppler_path = os.getenv("C:\Program Files (x86)\poppler\Library\ bin")
        
        # This makes the code more robust for Mac/Linux users as well
        # If poppler_path is None, pdf2image will try to find Poppler in the system PATH
        images = pdf2image.convert_from_bytes(uploaded_file.read(), poppler_path=poppler_path)
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
         app.logger.error("Poppler not found. Make sure it's installed and POPPLER_PATH is set correctly in .env for Windows.")
         raise Exception("Poppler not found. Ensure it is installed and the POPPLER_PATH in your .env file is correct.")
    except Exception as e:
        app.logger.error(f"Error processing PDF: {e}")
        raise Exception(f"Failed to process the PDF file. Ensure it's a valid PDF. Details: {e}")

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main page of the application."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_resume_endpoint():
    """Analyzes the resume against the job description."""
    app.logger.info("Received request for /analyze")

    if 'resume' not in request.files:
        return jsonify({"error": "No resume file was provided."}), 400

    file = request.files['resume']
    job_description = request.form.get('jobDescription', '').strip()
    prompt_type = request.form.get('promptType', 'analysis')

    if not job_description:
        return jsonify({"error": "Job description cannot be empty."}), 400

    prompts = {
        'analysis': """You are an HR specializing in recruitment. Analyze the following job description and resume. Determine how well 
                       the resume matches the job requirements. Highlight the candidate's relevant strengths and experiences.""",
        'match': """You are a skilled ATS tracker you need to show how much percentage the job discription match to the resume ...""",
        'skills': """You are a career development analyst you need to gave the user what are the missing skills in the resume corresponding to the job discription..."""
              }

    base_prompt = prompts.get(prompt_type)
    if not base_prompt:
        return jsonify({"error": "Invalid analysis type specified."}), 400
    
    input_text = f"**JOB DESCRIPTION:**\n{job_description}\n\n**TASK:**\n{base_prompt}"

    try:
        pdf_content = setup_pdf_image(file)
        response_text = get_gemini_response(input_text, pdf_content)
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5000, debug=True)