import google.generativeai as genai
import datetime
import base64
import os
from typing import List, Dict, Optional

# Configure API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Use the correct model
MODEL_NAME = "gemini-1.5-pro-latest"
model = genai.GenerativeModel(MODEL_NAME)

def pdf_to_base64(pdf_path: str) -> str:
    """Converts a PDF file to a base64 encoded string."""
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode("utf-8")

def extract_course_data_from_pdf(pdf_path: str) -> Dict:
    """Extracts course data from a PDF using Gemini API."""
    pdf_base64 = pdf_to_base64(pdf_path)

    prompt = """
    Extract the course data from the provided PDF. The PDF contains course information, including course names, descriptions, prerequisites, and credit hours.
    Structure the data as a Python dictionary. Each major should be a key, and for each major, include "required", "electives", "prerequisites", and "credit_hours" keys.

    Example structure:
    {
        "Computer Science": {
            "required": ["CS101", "CS102", ...],
            "electives": ["AI", "Machine Learning", ...],
            "prerequisites": {"CS102": ["CS101"], ...},
            "credit_hours": {"CS101": 3, ...}
        },
        "Mathematics": {...}
    }
    Return only the Python dictionary.
    """

    try:
        response = model.generate_content([prompt, pdf_base64])
        course_data = eval(response.text)  # Be careful with eval; consider using `json.loads` if possible
        return course_data
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return {}

def get_next_semester_courses(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
    graduation: datetime.date,
    notes: str,
    course_data: Dict
) -> Dict[str, List[str]]:
    """Determines the next semester's courses based on input."""
    
    if major not in course_data:
        return {"error": f"Major '{major}' not found."}

    required_courses = course_data[major]["required"]
    electives = course_data[major]["electives"]
    prerequisites = course_data[major]["prerequisites"]
    credit_hours = course_data[major]["credit_hours"]

    remaining_required = [c for c in required_courses if c not in course]
    available_electives = [e for e in electives if e not in course]

    next_semester_courses = []
    total_hours = 0

    for c in remaining_required:
        if all(prerequisite in course for prerequisite in prerequisites.get(c, [])):
            next_semester_courses.append(c)
            total_hours += credit_hours[c]
            if total_hours >= 18:
                break

    # Check if the user requested a minimum number of hours
    if "min_hours" in notes.lower():
        try:
            min_hours = int(notes.lower().split("min_hours:")[1].split()[0])
            if total_hours < min_hours:
                for e in available_electives:
                    if all(prerequisite in course for prerequisite in prerequisites.get(e, [])):
                        next_semester_courses.append(e)
                        total_hours += credit_hours[e]
                        if total_hours >= 18:
                            break
        except (IndexError, ValueError):
            return {"error": "Invalid format for min_hours in notes."}

    return {"courses": next_semester_courses, "total_hours": total_hours}

def generate_graduation_plan(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
    graduation: datetime.date,
    notes: str,
    course_data: Dict
) -> str:
    """Generates a graduation plan."""

    remaining_courses = course_data[major]["required"] + course_data[major]["electives"]
    remaining_courses = [c for c in remaining_courses if c not in course]
    
    prompt = f"""
    Given the student's degree: {degree}, major: {major}, minor: {minor}, courses taken: {course}, graduation month and year: {graduation.strftime('%Y-%m')}, and notes: {notes}, create a graduation plan.

    Remaining courses: {remaining_courses}

    Include a semester-by-semester plan, and list the number of credit hours for each semester.
    """

    response = model.generate_content(prompt)
    return response.text

def get_course_recommendations(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
    graduation: datetime.date,
    notes: str,
    course_data: Dict
) -> str:
    """Generates course recommendations and a graduation plan."""

    next_semester = get_next_semester_courses(degree, major, minor, course, graduation, notes, course_data)
    if "error" in next_semester:
        return next_semester["error"]

    next_semester_courses = next_semester["courses"]
    total_hours = next_semester["total_hours"]

    graduation_plan = generate_graduation_plan(degree, major, minor, course, graduation, notes, course_data)

    prompt_for_chat = f"""
    The student's next semester courses are: {next_semester_courses}, with a total of {total_hours} credit hours.
    Here is their graduation plan: \n {graduation_plan}

    Format the response as if you are a helpful academic advisor in a chat box.
    Then, at the end of your response, ask if any adjustments need to be made to the course selection.
    """

    chat_response = model.generate_content(prompt_for_chat)

    return chat_response.text

# Main program flow:
pdf_path = "pvcoursedata.pdf"
course_data = extract_course_data_from_pdf(pdf_path)

def process_frontend_input(frontend_data):
    """Processes input from the frontend and returns course recommendations."""
    
    if not course_data:
        return "Failed to extract course data from PDF."

    degree = frontend_data.get('degree')
    major = frontend_data.get('major')
    minor = frontend_data.get('minor')
    course_list = frontend_data.get('course')
    graduation_str = frontend_data.get('graduation')
    notes = frontend_data.get('notes')

    try:
        graduation = datetime.datetime.strptime(graduation_str, "%Y-%m").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM."

    try:
        recommendations = get_course_recommendations(degree, major, minor, course_list, graduation, notes, course_data)
        return recommendations
    except Exception as e:
        return f"An error occurred: {e}"

# Example frontend input:
frontend_data = {
    'degree': 'Bachelor of Science',
    'major': 'Computer Science',
    'minor': None,
    'course': ['CS101', 'Calculus I'],
    'graduation': '2026-05',
    'notes': 'min_hours: 15',
}

# Run and print response
chat_response = process_frontend_input(frontend_data)
print(chat_response)
