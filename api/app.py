from flask import Flask, request, jsonify, render_template_string
import PyPDF2
#import google.generativeai as genai
import os
import io
import json
from werkzeug.utils import secure_filename

from google import genai
from google.genai import types

app = Flask(__name__)

from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Parser Agent</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }
        .upload-area:hover {
            border-color: #764ba2;
            background-color: #f8f9ff;
        }
        .upload-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }
        .upload-btn:hover {
            transform: translateY(-2px);
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .results {
            display: none;
            margin-top: 30px;
        }
        .result-section {
            background: #f8f9ff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        .result-section h3 {
            color: #333;
            margin-top: 0;
        }
        .tech-stack {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        .tech-item {
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 14px;
        }
        .error {
            color: #e74c3c;
            background: #ffeaea;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #e74c3c;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Resume Parser Bot</h1>
        <div class="upload-area">
            <input type="file" id="fileInput" accept=".pdf" style="display: none;">
            <div onclick="document.getElementById('fileInput').click()">
                <h3>📄 Upload Resume (PDF)</h3>
                <p>Click here to select a PDF file</p>
                <button class="upload-btn">Choose File</button>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing resume...</p>
        </div>
        
        <div class="error" id="error"></div>
        
        <div class="results" id="results">
            <div class="result-section">
                <h3>👤 Personal Information</h3>
                <p id="name"></p>
            </div>
            
            <div class="result-section">
                <h3>💼 Experience</h3>
                <p id="experience"></p>
            </div>
            
            <div class="result-section">
                <h3>🛠️ Tech Stack</h3>
                <div class="tech-stack" id="techStack"></div>
            </div>
            
            <div class="result-section">
                <h3>🚀 Projects</h3>
                <div id="projects"></div>
            </div>
            
            <div class="result-section">
                <h3>📋 Summary</h3>
                <p id="summary"></p>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadFile(file);
            }
        });

        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('resume', file);
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            
            try {
                const response = await fetch('/parse', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                } else {
                    displayResults(data);
                }
            } catch (error) {
                showError('Failed to process resume. Please try again.');
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        function displayResults(data) {
            document.getElementById('name').textContent = data.name || 'Not found';
            document.getElementById('experience').textContent = data.experience || 'Not found';
            document.getElementById('summary').textContent = data.summary || 'Not found';
            
            // Display tech stack
            const techStackDiv = document.getElementById('techStack');
            techStackDiv.innerHTML = '';
            if (data.tech_stack && data.tech_stack.length > 0) {
                data.tech_stack.forEach(tech => {
                    const techItem = document.createElement('span');
                    techItem.className = 'tech-item';
                    techItem.textContent = tech;
                    techStackDiv.appendChild(techItem);
                });
            } else {
                techStackDiv.innerHTML = '<p>No tech stack found</p>';
            }
            
            // Display projects
            const projectsDiv = document.getElementById('projects');
            projectsDiv.innerHTML = '';
            if (data.projects && data.projects.length > 0) {
                data.projects.forEach(project => {
                    const projectElement = document.createElement('div');
                    projectElement.style.marginBottom = '10px';
                    projectElement.innerHTML = `<strong>• ${project}</strong>`;
                    projectsDiv.appendChild(projectElement);
                });
            } else {
                projectsDiv.innerHTML = '<p>No projects found</p>';
            }
            
            document.getElementById('results').style.display = 'block';
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
    </script>
</body>
</html>
"""

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")
    
def parse_resume_with_gemini(resume_text):
    """Parse resume using Gemini AI"""
    prompt = f"""
    Analyze the following resume text and extract the requested information. 
    Return the response in valid JSON format with the following structure:
    {{
        "name": "Full name of the person",
        "experience": "Summary of work experience with years",
        "tech_stack": ["list", "of", "technologies", "skills"],
        "projects": ["list of project names or descriptions"],
        "summary": "A brief professional summary of the candidate"
    }}

    Resume text:
    {resume_text}

    Important: Return only valid JSON, no additional text or formatting.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001', contents={prompt}
        )    

        result_text = response.text.strip()
        
        # Clean up the response to extract JSON
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        
        result_text = result_text.strip()
        
        # Parse JSON response
        parsed_result = json.loads(result_text)
        return parsed_result
        
    except json.JSONDecodeError as e:
        # Fallback: try to extract information manually if JSON parsing fails
        return {
            "name": "Could not extract name",
            "experience": "Could not extract experience details",
            "tech_stack": ["Could not extract tech stack"],
            "projects": ["Could not extract projects"],
            "summary": "Could not generate summary due to parsing error"
        }
    except Exception as e:
        raise Exception(f"Error with Gemini API: {str(e)}")
    
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/parse', methods=['POST'])
def parse_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400

        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Please upload a PDF file'}), 400

        # Extract text from PDF
        resume_text = extract_text_from_pdf(file)

        if not resume_text.strip():
            return jsonify({'error': 'Could not extract text from PDF'}), 400

        # Parse with Gemini
        parsed_data = parse_resume_with_gemini(resume_text)

        return jsonify(parsed_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


app = app