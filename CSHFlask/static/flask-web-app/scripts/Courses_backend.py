import google.generativeai as genai
import os
from typing import List, Dict, Optional
import re
import pdfplumber
from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure API Key
GOOGLE_API_KEY = 'AIzaSyCAudQfhOAC0Tvdq7Im75lVfIRdjnDfpjI'

genai.configure(api_key=GOOGLE_API_KEY)

# Use the correct model
MODEL_NAME = "gemini-1.5-pro-latest"
model = genai.GenerativeModel(MODEL_NAME)

def remove_asterisks(response: str) -> str:
    """Removes asterisks from the response."""
    return re.sub(r'\*+', '', response)

def extract_course_data_from_pdf(pdf_path: str) -> Dict:
    """Extracts course data from a PDF."""
    course_data = {}
    
    try:
        # Extract text from PDF using pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
        
        # Define course tags
        course_tags = [
            "ACCT", "EACC", "AFAM", "AGHR", "AGEC", "AGEG", "AGRI", "AGRO", "AFSC", "ANSC", "ARAB", "ARCH", "ARMY", "ARTS",
            "BIOL", "BCOM", "BLAW", "CHEG", "CHEM", "CHIN", "CVEG", "CPSY", "COMM", "CODE", "CPET", "CINS", "COMP", "CONS",
            "CNSL", "CRIJ", "CRJS", "CURR", "CUIN", "DANC", "DGMA", "EDBA", "DRAM", "ECED", "ECON", "EECO", "ADMN", "EDUL",
            "EDFN", "EDTC", "ELEG", "ELET", "ENGL", "ENTR", "ESPT", "FINA", "EFIN", "PVEX", "FDSC", "FREN", "GNEG", "GNST",
            "GEOG", "HKIN", "HLTH", "HIST", "HCOL", "HDFM", "HUMA", "HUNF", "HUSC", "FLLT", "JPSY", "JJUS", "KINE", "EMGM",
            "MISY", "MGMT", "EMCO", "EMRK", "MRKT", "MATH", "MCEG", "EMIS", "MUSC", "NRES", "NAVY", "NURS", "NUTR", "PHIL",
            "PHED", "PHSC", "PHYS", "POSC", "PSYC", "PHLT", "RDNG", "REST", "SOWK", "SOCG", "SPAN", "SPED", "SPMT", "SUPV",
            "SCMG"
        ]
        
        # Example: Look for course names and prerequisites in the extracted text
        lines = text.split("\n")
        
        for line in lines:
            # Debug: Print each line being processed
            #print(f"Processing line: {line}")
            
            # Example course data parsing, modify according to your PDF structure
            match = re.match(r"([A-Z]{4})\s+(\d{4})", line)
            if match:
                course_tag = match.group(1)
                print(f"Match found: {match.groups()}")
                if course_tag in course_tags:
                    course_code = f"{match.group(1)} {match.group(2)}"
                    prerequisites = re.findall(r"Prerequisites?: ([A-Z]{4} \d{4})", line)
                    corequisites = re.findall(r"Corequisites?: ([A-Z]{4} \d{4})", line)

                    if course_tag not in course_data:
                        course_data[course_tag] = {"required": [], "electives": [], "prerequisites": {}, "credit_hours": {}}

                    course_data[course_tag]["required"].append(course_code)
                    course_data[course_tag]["prerequisites"][course_code] = prerequisites + corequisites
        
    except Exception as e:
        print(f"Error extracting course data from PDF: {e}")
        return {}

    return course_data

def get_course_recommendations(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
    notes: str,
    graduation: str,
    course_data: Dict
) -> str:
    """Generates course recommendations and a graduation plan."""
    
    prompt_for_chat = f"""
    The student's major is: {major}, and they're pursuing a {degree} degree. They have taken the following courses: {course}.
    Based on this information, recommend the next semester's courses and provide a graduation plan. Give specifically what courses the student should take each term, and if there's an elective, then mention which elective(ex. creative arts core, COMP elective, etc). PVAMU's courses are listed here: {course_data}
    The student's notes are: {notes}. It is currently Spring 2025 and they want to graduate by {graduation}.

    Format the response as if you are a helpful academic advisor in a chat box.
    Then, at the end of your response, ask if any adjustments need to be made to the course selection.
    """

    chat_response = model.generate_content(prompt_for_chat)

    return remove_asterisks(chat_response.text)

# Main program flow:
def process_frontend_input(frontend_data):
    """Processes input from the frontend and returns course recommendations."""
    
    # Extract course data from PDF
    course_data = extract_course_data_from_pdf('/Users/hameedalatishe/Documents/GitHub/CSHTidal/CSHFlask/static/flask-web-app/static/pdfs/pvcoursedata.pdf')  # Fixed PDF path
    if not course_data:
        return "Failed to extract course data from PDF."

    degree = frontend_data.get('degree')
    major = frontend_data.get('major')
    minor = frontend_data.get('minor')
    course_list = frontend_data.get('course')
    notes = frontend_data.get('notes')
    graduation = frontend_data.get('graduation')

    try:
        recommendations = get_course_recommendations(degree, major, minor, course_list, notes, graduation, course_data)
        return recommendations
    except Exception as e:
        return f"An error occurred: {e}"