from flask import Blueprint, render_template, request, redirect, url_for, flash
from scripts.Courses_backend import process_frontend_input

main = Blueprint('main', __name__)

# Landing Page Route (Starting Page)
@main.route('/', methods=['GET'])
def index():
    return render_template('landing.html')  # Show landing page first

# Get started Route
@main.route('/getstarted', methods=['POST'])
def getstarted():
    return render_template('form.html')  # Show get started

# Sign-in Route (Redirects to Form Page)
@main.route('/signin', methods=['POST'])
def signin():
    username = request.form.get("username")
    password = request.form.get("password")

    # TODO: Add authentication logic if needed

    return redirect(url_for('main.form_page'))  # Redirect to form page

# Form Page Route
@main.route('/form', methods=['GET'])
def form_page():
    return render_template('form.html')  # Render the form page

# Submit Form Route
@main.route('/submit_form', methods=['POST'])
def submit_form():
    try:
        degree = request.form.get('degree')
        major = request.form.get('major')
        minor = request.form.get('minor')
        course = request.form.getlist('course[]')
        graduation = request.form.get('graduation')
        notes = request.form.get('notes')

        # Prepare the frontend data
        frontend_data = {
            'degree': degree,
            'major': major,
            'minor': minor,
            'course': course,
            'graduation': graduation,
            'notes': notes,
        }

        # Process the frontend data
        response = process_frontend_input(frontend_data)

        # Redirect to the dashboard with the response data
        return redirect(url_for('main.dashboard', response=response))
    except Exception as e:
        return f"An error occurred: {e}", 400

# Dashboard Route
@main.route('/dashboard')
def dashboard():
    response = request.args.get('response')
    return render_template('dashboard.html', response=response)