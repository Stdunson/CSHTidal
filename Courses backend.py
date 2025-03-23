import google.generativeai as genai
import datetime
import os
from typing import List, Dict, Optional
import logging
import json
import re
import pdfplumber

# Configure API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
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
    
    # Extract text from PDF using pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    
    # Here you would parse the extracted text to populate course data.
    # This is just a simple example, and you may need more advanced text processing depending on the PDF structure.
    
    # Example: Look for course names and prerequisites in the extracted text
    lines = text.split("\n")
    
    current_major = None
    current_courses = {"required": [], "electives": [], "prerequisites": {}, "credit_hours": {}}
    
    for line in lines:
        # Look for major name (this is an example; you will need to adapt this based on the PDF)
        if "Computer Science" in line:
            current_major = "Computer Science"
        
        # Example course data parsing, modify according to your PDF structure
        if "CS" in line:
            course_info = line.split()  # Assuming something like "CS101 3 credits"
            if len(course_info) == 3:
                course_code = course_info[0]
                credit_hours = int(course_info[1])  # Example, assuming credit hours is the second item
                current_courses["required"].append(course_code)
                current_courses["credit_hours"][course_code] = credit_hours
        
        # You would expand on this logic based on your PDF's structure to extract all relevant courses and data

    # Store the extracted data into a dictionary by major
    course_data[current_major] = current_courses
    
    return course_data

def get_next_semester_courses(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
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
    notes: str,
    course_data: Dict
) -> str:
    """Generates a graduation plan."""
    
    remaining_courses = course_data[major]["required"] + course_data[major]["electives"]
    remaining_courses = [c for c in remaining_courses if c not in course]
    
    prompt = f"""
    Given the student's degree: {degree}, major: {major}, minor: {minor}, courses taken: {course}, and notes: {notes}, create a graduation plan.

    Remaining courses: {remaining_courses}

    Include a semester-by-semester plan, and list the number of credit hours for each semester.
    """

    response = model.generate_content(prompt)
    return remove_asterisks(response.text)

def get_course_recommendations(
    degree: str,
    major: str,
    minor: Optional[str],
    course: List[str],
    notes: str,
    course_data: Dict
) -> str:
    """Generates course recommendations and a graduation plan."""
    
    next_semester = get_next_semester_courses(degree, major, minor, course, notes, course_data)
    if "error" in next_semester:
        return next_semester["error"]

    next_semester_courses = next_semester["courses"]
    total_hours = next_semester["total_hours"]

    graduation_plan = generate_graduation_plan(degree, major, minor, course, notes, course_data)

    prompt_for_chat = f"""
    The student's next semester courses are: {next_semester_courses}, with a total of {total_hours} credit hours.
    Here is their graduation plan: \n {graduation_plan}

    Format the response as if you are a helpful academic advisor in a chat box.
    Then, at the end of your response, ask if any adjustments need to be made to the course selection.
    """

    chat_response = model.generate_content(prompt_for_chat)

    return remove_asterisks(chat_response.text)

# Main program flow:
def process_frontend_input(frontend_data):
    """Processes input from the frontend and returns course recommendations."""
    
    try:
        # Extract course data from PDF
        course_data = extract_course_data_from_pdf(frontend_data.get('pdf_path', 'pvcoursedata.pdf'))  # PDF path provided by the user
        if not course_data:
            return "Failed to extract course data from PDF."

        degree = frontend_data.get('degree')
        major = frontend_data.get('major')
        minor = frontend_data.get('minor')
        course_list = frontend_data.get('course')
        notes = frontend_data.get('notes')

        # Handle graduation input as before
        season_year = frontend_data.get('graduation')  # e.g., 'spring 2028'
        
        # Split input into season and year
        season, year = season_year.lower().split()
        
        # Check if the season is valid
        if season not in ["fall", "spring", "summer"]:
            return "Invalid season. Please use fall, spring, or summer."
        
        # Validate and parse the year as an integer
        try:
            graduation_year = int(year)
        except ValueError:
            return "Invalid year format. Please use a valid year (e.g., 2028)."

    except ValueError:
        return "Invalid format. Please use <season year> (e.g., spring 2028)."

    try:
        recommendations = get_course_recommendations(degree, major, minor, course_list, notes, course_data)
        return recommendations
    except Exception as e:
        return f"An error occurred: {e}"

# Example frontend input:
frontend_data = {
    'degree': 'Bachelor of Science',
    'major': 'Computer Science',
    'minor': None,
    'course': ['CS101', 'Calculus I'],
    'graduation': 'spring 2028',  # Example input with no dashes
    'notes': 'min_hours: 15',
    'pdf_path': 'pvcoursedata.pdf',  # Specify the PDF path
}

# Run and print response
chat_response = process_frontend_input(frontend_data)
print(chat_response)