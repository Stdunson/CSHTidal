import datetime
from typing import List, Dict, Optional
from google import genai, configure, Client, GenerativeModel
import base64

GOOGLE_API_KEY = "AIzaSyDcp5yex9vqJtGyIlVF56_K9v9tkyGL2-A"
configure(api_key=GOOGLE_API_KEY)
model = GenerativeModel("gemini-pro")
client = Client(api_key=GOOGLE_API_KEY)

def pdf_to_base64(pdf_path: str) -> str:
    """Converts a PDF file to a base64 encoded string."""
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode("utf-8")

def extract_course_data_from_pdf(pdf_path: str) -> Dict:
    """Extracts course data from a PDF using Gemini API."""
    pdf_base64 = pdf_to_base64(pdf_path)

    prompt = """
    Extract the course data from the provided PDF. The PDF contains course information, including course names, descriptions, prerequisites, and credit hours.
    Structure the data as a python dictionary. Each major should be a key, and for each major, there should be "required", "electives", "prerequisites", and "credit_hours" keys.

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
    Return only the python dictionary.
    """

    response = client.models.generate_content(prompt, parts=[pdf_base64])
    try:
        course_data = eval(response.text)
        return course_data
    except (SyntaxError, NameError, TypeError) as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Gemini response: {response.text}")
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

    if "min_hours" in notes.lower():  # Check for minimum hours request in notes
        min_hours = int(notes.lower().split("min_hours:")[1].split()[0]) #extracts the number after min_hours:
        if total_hours < min_hours:
            for e in available_electives:
                if all(prerequisite in course for prerequisite in prerequisites.get(e, [])):
                    next_semester_courses.append(e)
                    total_hours += credit_hours[e]
                    if total_hours >= 18:
                        break

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
    
    remaining_courses = course_data[major]["required"].copy()
    remaining_courses.extend(course_data[major]["electives"].copy())

    for c in course:
        if c in remaining_courses:
            remaining_courses.remove(c)
            
    prompt = f"""
    Given the student's degree: {degree}, major: {major}, minor: {minor}, courses taken: {course}, graduation month and year: {graduation.strftime('%Y-%m')}, and notes: {notes}, create a graduation plan.

    Remaining courses: {remaining_courses}

    Include a semester by semester plan, and include the amount of credit hours for each semester.
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

    if course_data:
        degree = frontend_data.get('degree')
        major = frontend_data.get('major')
        minor = frontend_data.get('minor')
        course_list = frontend_data.get('course')
        graduation_str = frontend_data.get('graduation')
        notes = frontend_data.get('notes')

        try:
            graduation = datetime.datetime.strptime(graduation_str, "%Y-%m").date()
        except ValueError:
            return "Invalid date format. Please use犃-MM."

        try:
            recommendations = get_course_recommendations(degree, major, minor, course_list, graduation, notes, course_data)
            return recommendations
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        return "Failed to extract course data from PDF."

# Example of how to use it with data from a frontend (replace with your actual frontend data):
frontend_data = {
    'degree': 'Bachelor of Science',
    'major': 'Computer Science',
    'minor': None,
    'course': ['CS101', 'Calculus I'],
    'graduation': '2026-05',
    'notes': 'min_hours: 15',
}

chat_response = process_frontend_input(frontend_data)
print(chat_response)