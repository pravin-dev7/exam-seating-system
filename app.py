# app.py - Main Flask Application

import os
import json
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, send_file, jsonify)
from werkzeug.utils import secure_filename

from config import Config
from auth import login_required, check_credentials, login_user, logout_user
from excel_loader import load_students_from_excel, validate_excel_format, get_department_summary
from seating_algorithm import generate_multiple_hall_distribution, get_seating_stats
from pdf_generator import generate_all_pdfs

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Ensure required directories exist
for folder in [Config.UPLOAD_FOLDER, Config.PDF_FOLDER, Config.LOGO_FOLDER]:
    os.makedirs(folder, exist_ok=True)


# ---------------------------------------------------------------------------
# Utility Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def save_session_data(key, data):
    """Save complex data in session as JSON string."""
    session[key] = json.dumps(data)


def load_session_data(key):
    """Load complex data from session JSON string."""
    raw = session.get(key)
    if raw:
        return json.loads(raw)
    return None


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if check_credentials(username, password):
            login_user()
            flash('Welcome back, Admin!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    students = load_session_data('students')
    halls = load_session_data('halls')
    stats = load_session_data('stats')
    exam_info = load_session_data('exam_info')

    return render_template('dashboard.html',
                           student_count=len(students) if students else 0,
                           halls_generated=len(halls) if halls else 0,
                           exam_info=exam_info,
                           stats=stats)


# ---------------------------------------------------------------------------
# Upload Routes
# ---------------------------------------------------------------------------

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('No file selected. Please choose an Excel file.', 'danger')
            return redirect(request.url)

        file = request.files['excel_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
            flash('Invalid file type. Please upload an .xlsx or .xls file.', 'danger')
            return redirect(request.url)

        filename = secure_filename(f"students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)

        # Validate format
        is_valid, message = validate_excel_format(filepath)
        if not is_valid:
            os.remove(filepath)
            flash(f'File validation failed: {message}', 'danger')
            return redirect(request.url)

        # Load students
        students, error = load_students_from_excel(filepath)
        if error:
            flash(f'Error loading file: {error}', 'danger')
            return redirect(request.url)

        dept_summary = get_department_summary(students)

        save_session_data('students', students)
        save_session_data('dept_summary', dept_summary)
        session['excel_filename'] = filename

        flash(f'✓ {message}', 'success')
        return redirect(url_for('generate'))

    return render_template('upload.html')


# ---------------------------------------------------------------------------
# Generate Seating Routes
# ---------------------------------------------------------------------------

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    students = load_session_data('students')
    dept_summary = load_session_data('dept_summary')

    if not students:
        flash('Please upload a student Excel file first.', 'warning')
        return redirect(url_for('upload'))

    if request.method == 'POST':
        # Collect form data
        college_name = request.form.get('college_name', '').strip()
        exam_name = request.form.get('exam_name', '').strip()
        exam_date = request.form.get('exam_date', '').strip()
        num_halls = int(request.form.get('num_halls', 1))
        benches_per_hall = int(request.form.get('benches_per_hall', 10))
        seats_per_bench = int(request.form.get('seats_per_bench', 3))
        flow_type = request.form.get('flow_type', 'mixed')

        # Validate capacity
        total_capacity = num_halls * benches_per_hall * seats_per_bench
        if total_capacity < len(students):
            flash(
                f'Insufficient capacity! You have {len(students)} students but only '
                f'{total_capacity} seats ({num_halls} halls × {benches_per_hall} benches × '
                f'{seats_per_bench} seats). Please increase halls or benches.',
                'danger'
            )
            return redirect(request.url)

        # Handle logo upload
        logo_path = ''
        if 'college_logo' in request.files:
            logo_file = request.files['college_logo']
            if logo_file and logo_file.filename != '' and \
               allowed_file(logo_file.filename, Config.ALLOWED_IMAGE_EXTENSIONS):
                logo_filename = secure_filename(f"logo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                logo_path = os.path.join(Config.LOGO_FOLDER, logo_filename)
                logo_file.save(logo_path)

        # Build exam info dict
        exam_info = {
            'college_name': college_name,
            'exam_name': exam_name,
            'exam_date': exam_date,
            'num_halls': num_halls,
            'benches_per_hall': benches_per_hall,
            'seats_per_bench': seats_per_bench,
            'flow_type': flow_type,
            'logo_path': logo_path,
            'total_capacity': total_capacity,
        }

        # Run seating algorithm
        halls = generate_multiple_hall_distribution(
            students, num_halls, benches_per_hall, seats_per_bench, flow_type
        )

        stats = get_seating_stats(halls)

        # Generate PDFs
        pdf_files = generate_all_pdfs(halls, exam_info, Config.PDF_FOLDER)

        # Save to session
        save_session_data('halls', halls)
        save_session_data('stats', stats)
        save_session_data('exam_info', exam_info)
        save_session_data('pdf_files', pdf_files)

        flash(f'✓ Seating arrangement generated successfully for {len(halls)} hall(s)!', 'success')
        return redirect(url_for('seating_result'))

    return render_template('generate.html',
                           students=students,
                           dept_summary=dept_summary,
                           seating_flows=Config.SEATING_FLOWS,
                           student_count=len(students))


# ---------------------------------------------------------------------------
# Seating Result & Download
# ---------------------------------------------------------------------------

@app.route('/seating-result')
@login_required
def seating_result():
    halls = load_session_data('halls')
    stats = load_session_data('stats')
    exam_info = load_session_data('exam_info')
    pdf_files = load_session_data('pdf_files')

    if not halls:
        flash('No seating arrangement found. Please generate one first.', 'warning')
        return redirect(url_for('generate'))

    return render_template('seating_result.html',
                           halls=halls,
                           stats=stats,
                           exam_info=exam_info,
                           pdf_files=pdf_files)


@app.route('/download-pdf/<int:hall_number>')
@login_required
def download_pdf(hall_number):
    pdf_files = load_session_data('pdf_files')
    if not pdf_files:
        flash('No PDFs found. Please generate seating first.', 'warning')
        return redirect(url_for('dashboard'))

    for pdf in pdf_files:
        if pdf['hall_number'] == hall_number:
            filepath = pdf['path']
            if os.path.exists(filepath):
                return send_file(filepath,
                                 as_attachment=True,
                                 download_name=pdf['filename'],
                                 mimetype='application/pdf')

    flash(f'PDF for Hall {hall_number} not found.', 'danger')
    return redirect(url_for('seating_result'))


@app.route('/download-all-pdfs')
@login_required
def download_all_pdfs():
    """Create a zip of all PDFs and serve it."""
    import zipfile
    import io

    pdf_files = load_session_data('pdf_files')
    if not pdf_files:
        flash('No PDFs found. Please generate seating first.', 'warning')
        return redirect(url_for('dashboard'))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pdf in pdf_files:
            if os.path.exists(pdf['path']):
                zf.write(pdf['path'], pdf['filename'])

    memory_file.seek(0)
    exam_info = load_session_data('exam_info')
    exam_name = exam_info.get('exam_name', 'Exam').replace(' ', '_') if exam_info else 'Exam'
    zip_name = f"{exam_name}_All_Seating_Plans.zip"

    return send_file(memory_file,
                     as_attachment=True,
                     download_name=zip_name,
                     mimetype='application/zip')


# ---------------------------------------------------------------------------
# Drag & Drop Seat Editor
# ---------------------------------------------------------------------------

@app.route('/seating-preview')
@login_required
def seating_preview():
    """Render the drag-and-drop seat editor page."""
    halls     = load_session_data('halls')
    exam_info = load_session_data('exam_info')

    if not halls:
        flash('No seating arrangement found. Please generate one first.', 'warning')
        return redirect(url_for('generate'))

    return render_template('seating_preview.html',
                           halls=halls,
                           exam_info=exam_info)


@app.route('/save_seating', methods=['POST'])
@login_required
def save_seating():
    """
    Receive updated halls JSON from drag-and-drop editor via fetch/AJAX.
    Persists the new arrangement to session and regenerates PDFs.
    """
    try:
        payload = request.get_json(force=True)
        if not payload or 'halls' not in payload:
            return jsonify({'success': False, 'message': 'Invalid payload — missing halls data.'}), 400

        updated_halls = payload['halls']

        # Basic validation: each hall must have hall_number and benches
        for hall in updated_halls:
            if 'hall_number' not in hall or 'benches' not in hall:
                return jsonify({'success': False, 'message': 'Malformed hall data.'}), 400

        # Recompute total_students per hall after swaps
        for hall in updated_halls:
            hall['total_students'] = sum(
                1 for bench in hall['benches']
                for seat in bench
                if seat is not None
            )

        # Recompute stats
        stats = get_seating_stats(updated_halls)

        # Persist to session
        save_session_data('halls', updated_halls)
        save_session_data('stats', stats)

        # Regenerate PDFs with updated arrangement
        exam_info = load_session_data('exam_info')
        if exam_info:
            try:
                pdf_files = generate_all_pdfs(updated_halls, exam_info, Config.PDF_FOLDER)
                save_session_data('pdf_files', pdf_files)
            except Exception as pdf_err:
                app.logger.warning(f'PDF regeneration failed after save: {pdf_err}')

        return jsonify({
            'success': True,
            'message': f'Seating saved. {stats["total_students"]} students across {stats["total_halls"]} halls.',
            'stats': stats
        })

    except Exception as e:
        app.logger.error(f'save_seating error: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# API Endpoints (for JS)
# ---------------------------------------------------------------------------

@app.route('/api/stats')
@login_required
def api_stats():
    stats = load_session_data('stats')
    return jsonify(stats or {})


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('login.html'), 404


@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 16MB.', 'danger')
    return redirect(url_for('upload'))


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("=" * 60)
    print("  AI Exam Seating Arrangement System")
    print("  Starting server at http://127.0.0.1:5000")
    print("  Login: admin / admin123")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
