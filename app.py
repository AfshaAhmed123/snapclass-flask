from dotenv import load_dotenv
load_dotenv()
 
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from src.database.db import (
    check_teacher_exists, create_teacher, teacher_login,
    get_teacher_subjects, get_attendance_for_teacher,
    get_all_students, create_student, get_student_subjects,
    get_student_attendance, enroll_student_to_subject,
    unenroll_student_to_subject, create_subject, create_attendance
)
from src.pipelines.face_pipeline import get_face_embeddings, predict_attendance, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding, process_bulk_audio
from src.utils.email_utils import send_absence_email
from datetime import datetime
import numpy as np
from PIL import Image
import io, base64, segno, os
from functools import wraps
 
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'snapclass-afsha-ahmed-2026')
 
# ── Login Required Decorator ──────────────────────────────────────────────────
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get('is_logged_in'):
                return redirect(url_for('home'))
            if role and session.get('user_role') != role:
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return wrapper
    return decorator
 
# ── Pages ─────────────────────────────────────────────────────────────────────
 
@app.route('/')
def home():
    if session.get('is_logged_in'):
        if session.get('user_role') == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('home.html')
 
@app.route('/teacher')
def teacher_portal():
    return render_template('teacher_login.html')
 
@app.route('/student')
def student_portal():
    return render_template('student_login.html')
 
@app.route('/teacher/dashboard')
@login_required(role='teacher')
def teacher_dashboard():
    teacher = session.get('teacher_data', {})
    subjects = get_teacher_subjects(teacher.get('teacher_id'))
    return render_template('teacher_dashboard.html', teacher=teacher, subjects=subjects)
 
@app.route('/student/dashboard')
@login_required(role='student')
def student_dashboard():
    student = session.get('student_data', {})
    student_id = student.get('student_id')
    subjects = get_student_subjects(student_id)
    logs = get_student_attendance(student_id)
 
    stats_map = {}
    for log in logs:
        sid = log['subject_id']
        if sid not in stats_map:
            stats_map[sid] = {'total': 0, 'attended': 0}
        stats_map[sid]['total'] += 1
        if log.get('is_present'):
            stats_map[sid]['attended'] += 1
 
    return render_template('student_dashboard.html', student=student,
                           subjects=subjects, stats_map=stats_map)
 
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
 
# ── Teacher Auth ──────────────────────────────────────────────────────────────
 
@app.route('/api/teacher/login', methods=['POST'])
def api_teacher_login():
    data = request.get_json()
    teacher = teacher_login(data.get('username'), data.get('password'))
    if teacher:
        session['is_logged_in'] = True
        session['user_role'] = 'teacher'
        session['teacher_data'] = teacher
        return jsonify({'success': True, 'name': teacher['name']})
    return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
 
@app.route('/api/teacher/register', methods=['POST'])
def api_teacher_register():
    data     = request.get_json()
    username = data.get('username', '').strip()
    name     = data.get('name', '').strip()
    password = data.get('password', '')
    confirm  = data.get('confirm', '')
 
    if not username or not name or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    if password != confirm:
        return jsonify({'success': False, 'message': "Passwords don't match"}), 400
    if check_teacher_exists(username):
        return jsonify({'success': False, 'message': 'Username already taken'}), 400
 
    create_teacher(username, password, name)
    return jsonify({'success': True, 'message': 'Account created! Please login.'})
 
# ── Subjects ──────────────────────────────────────────────────────────────────
 
@app.route('/api/subjects', methods=['GET'])
@login_required(role='teacher')
def api_get_subjects():
    teacher_id = session['teacher_data']['teacher_id']
    return jsonify(get_teacher_subjects(teacher_id))
 
@app.route('/api/subjects/create', methods=['POST'])
@login_required(role='teacher')
def api_create_subject():
    data = request.get_json()
    teacher_id = session['teacher_data']['teacher_id']
    try:
        create_subject(data['code'], data['name'], data['section'], teacher_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
 
@app.route('/api/subjects/delete', methods=['POST'])
@login_required(role='teacher')
def api_delete_subject():
    from src.database.config import supabase
    data = request.get_json()
    subject_id = data.get('subject_id')
    teacher_id = session['teacher_data']['teacher_id']
    try:
        check = supabase.table('subjects').select('subject_id').eq('subject_id', subject_id).eq('teacher_id', teacher_id).execute()
        if not check.data:
            return jsonify({'success': False, 'message': 'Subject not found'}), 404
        supabase.table('attendance_logs').delete().eq('subject_id', subject_id).execute()
        supabase.table('subject_students').delete().eq('subject_id', subject_id).execute()
        supabase.table('subjects').delete().eq('subject_id', subject_id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
 
# ── QR Code — FIXED: added @app.route and https:// + encodeURIComponent-safe URL ──
@app.route('/api/subjects/<subject_id>/qr')
@login_required(role='teacher')
def api_subject_qr(subject_id):
    from src.database.config import supabase
    from urllib.parse import quote
    res = supabase.table('subjects').select('subject_code, name').eq('subject_id', subject_id).execute()
    if not res.data:
        return jsonify({'error': 'Not found'}), 404
    sub = res.data[0]
    # ✅ Fixed: https:// added and subject_code is URL-encoded (no spaces in QR)
    join_url = f"https://snapclass.app/?join-code={quote(sub['subject_code'])}"
    qr = segno.make(join_url)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=8, border=1)
    b64 = base64.b64encode(out.getvalue()).decode()
    return jsonify({'qr': b64, 'url': join_url, 'code': sub['subject_code'], 'name': sub['name']})
 
# ── Attendance ────────────────────────────────────────────────────────────────
 
@app.route('/api/attendance/face', methods=['POST'])
@login_required(role='teacher')
def api_face_attendance():
    from src.database.config import supabase
    subject_id = request.form.get('subject_id')
    files = request.files.getlist('photos')
 
    if not files:
        return jsonify({'success': False, 'message': 'No photos uploaded'}), 400
 
    all_detected = {}
    for f in files:
        img = np.array(Image.open(f).convert('RGB'))
        detected, _, _ = predict_attendance(img)
        for sid in detected:
            all_detected.setdefault(int(sid), []).append(f.filename or 'photo')
 
    enrolled_res = supabase.table('subject_students').select('*, students(*)').eq('subject_id', subject_id).execute()
    enrolled = enrolled_res.data
 
    if not enrolled:
        return jsonify({'success': False, 'message': 'No students enrolled'}), 400
 
    results, logs = [], []
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
 
    for node in enrolled:
        student = node['students']
        sources = all_detected.get(int(student['student_id']), [])
        is_present = len(sources) > 0
        results.append({'name': student['name'], 'id': student['student_id'],
                        'status': 'present' if is_present else 'absent'})
        logs.append({'student_id': student['student_id'], 'subject_id': subject_id,
                     'timestamp': timestamp, 'is_present': is_present})
 
    return jsonify({'success': True, 'results': results, 'logs': logs})
 
@app.route('/api/attendance/voice', methods=['POST'])
@login_required(role='teacher')
def api_voice_attendance():
    from src.database.config import supabase
    subject_id = request.form.get('subject_id')
    audio_file = request.files.get('audio')
 
    if not audio_file:
        return jsonify({'success': False, 'message': 'No audio uploaded'}), 400
 
    enrolled_res = supabase.table('subject_students').select('*, students(*)').eq('subject_id', subject_id).execute()
    enrolled = enrolled_res.data
 
    candidates = {s['students']['student_id']: s['students'].get('voice_embedding')
                  for s in enrolled if s['students'].get('voice_embedding')}
 
    if not candidates:
        return jsonify({'success': False, 'message': 'No voice profiles registered'}), 400
 
    detected = process_bulk_audio(audio_file.read(), candidates)
    results, logs = [], []
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
 
    for node in enrolled:
        student = node['students']
        score = detected.get(student['student_id'], 0.0)
        is_present = bool(score > 0)
        results.append({'name': student['name'], 'id': student['student_id'],
                        'status': 'present' if is_present else 'absent'})
        logs.append({'student_id': student['student_id'], 'subject_id': subject_id,
                     'timestamp': timestamp, 'is_present': is_present})
 
    return jsonify({'success': True, 'results': results, 'logs': logs})
 
@app.route('/api/attendance/confirm', methods=['POST'])
@login_required(role='teacher')
def api_confirm_attendance():
    data         = request.get_json()
    logs         = data.get('logs', [])
    subject_name = data.get('subject_name', 'the subject')
 
    create_attendance(logs)
 
    email_alerts = []
    for log in logs:
        if not log.get('is_present'):
            result = send_absence_email(log.get('student_name', 'Student'), subject_name)
            email_alerts.append(result)
 
    return jsonify({'success': True, 'email_alerts': email_alerts})
 
@app.route('/api/attendance/records')
@login_required(role='teacher')
def api_attendance_records():
    teacher_id = session['teacher_data']['teacher_id']
    records    = get_attendance_for_teacher(teacher_id)
    data = []
    for r in records:
        ts = r.get('timestamp')
        data.append({
            'time':         datetime.fromisoformat(ts).strftime('%Y-%m-%d %I:%M %p') if ts else 'N/A',
            'subject':      r['subjects']['name'],
            'subject_code': r['subjects']['subject_code'],
            'is_present':   bool(r.get('is_present', False))
        })
    return jsonify(data)
 
# ── Student Auth ──────────────────────────────────────────────────────────────
 
@app.route('/api/student/face-login', methods=['POST'])
def api_student_face_login():
    photo = request.files.get('photo')
    if not photo:
        return jsonify({'success': False, 'message': 'No photo'}), 400
 
    img = np.array(Image.open(photo).convert('RGB'))
    detected, _, num_faces = predict_attendance(img)
 
    if num_faces == 0:
        return jsonify({'success': False, 'message': 'No face found'})
    if num_faces > 1:
        return jsonify({'success': False, 'message': 'Multiple faces detected'})
    if not detected:
        return jsonify({'success': False, 'message': 'Face not recognized', 'new_student': True})
 
    student_id   = list(detected.keys())[0]
    all_students = get_all_students()
    student      = next((s for s in all_students if s['student_id'] == student_id), None)
 
    if student:
        session['is_logged_in'] = True
        session['user_role']    = 'student'
        session['student_data'] = student
        return jsonify({'success': True, 'name': student['name']})
 
    return jsonify({'success': False, 'message': 'Student not found'})
 
@app.route('/api/student/register', methods=['POST'])
def api_student_register():
    name  = request.form.get('name', '').strip()
    photo = request.files.get('photo')
    audio = request.files.get('audio')
 
    if not name or not photo:
        return jsonify({'success': False, 'message': 'Name and photo are required'}), 400
 
    img       = np.array(Image.open(photo).convert('RGB'))
    encodings = get_face_embeddings(img)
 
    if not encodings:
        return jsonify({'success': False, 'message': 'Could not capture face features'}), 400
 
    face_emb  = encodings[0].tolist()
    voice_emb = None
    if audio:
        voice_emb = get_voice_embedding(audio.read())
 
    student_data = create_student(name, face_embedding=face_emb, voice_embedding=voice_emb)
    if student_data:
        train_classifier()
        student = student_data[0]
        session['is_logged_in'] = True
        session['user_role']    = 'student'
        session['student_data'] = student
        return jsonify({'success': True, 'name': name})
 
    return jsonify({'success': False, 'message': 'Registration failed'}), 500
 
@app.route('/api/student/enroll', methods=['POST'])
@login_required(role='student')
def api_student_enroll():
    from src.database.config import supabase
    data       = request.get_json()
    join_code  = data.get('code', '').strip().upper()
    student_id = session['student_data']['student_id']
 
    res = supabase.table('subjects').select('subject_id, name').eq('subject_code', join_code).execute()
    if not res.data:
        return jsonify({'success': False, 'message': 'Subject code not found'}), 404
 
    subject = res.data[0]
    check   = supabase.table('subject_students').select('*').eq('subject_id', subject['subject_id']).eq('student_id', student_id).execute()
    if check.data:
        return jsonify({'success': False, 'message': 'Already enrolled'}), 400
 
    enroll_student_to_subject(student_id, subject['subject_id'])
    return jsonify({'success': True, 'subject_name': subject['name']})
 
@app.route('/api/student/unenroll', methods=['POST'])
@login_required(role='student')
def api_student_unenroll():
    data       = request.get_json()
    student_id = session['student_data']['student_id']
    unenroll_student_to_subject(student_id, data.get('subject_id'))
    return jsonify({'success': True})
 
if __name__ == '__main__':
    app.run(debug=True, port=5002)