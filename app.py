import os
import sqlite3
import threading
import cv2
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort, send_from_directory
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message



# ==================== APP INITIALIZATION ====================
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
# Configure email settings

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # REPLACE WITH YOUR EMAIL
app.config['MAIL_PASSWORD'] = 'your_app_password'     # REPLACE WITH YOUR APP PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'

mail = Mail(app)
# ==================== FOLDER CONFIGURATIONS ====================
CCTV_FOLDER = os.path.join('static', 'videos')  # folder where videos are stored
SEARCH_FOLDER = 'static/search_results'
COMPLAINT_FOLDER = os.path.join(os.getcwd(), 'static', 'complaint_photos')

# Create necessary directories
os.makedirs(SEARCH_FOLDER, exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/cctv', exist_ok=True)
os.makedirs(COMPLAINT_FOLDER, exist_ok=True)
os.makedirs('static/search_clips', exist_ok=True)

# ==================== DATABASE HELPER FUNCTIONS ====================
def get_db():
    # Adding check_same_thread=False is CRITICAL for background searching
    conn = sqlite3.connect('FaceTrace.db', timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cases table with new columns
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                photo TEXT,
                description TEXT,
                identifying_marks TEXT,
                last_seen_location TEXT,
                last_seen_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'missing',
                found_location TEXT,
                found_date DATE,
                found_notes TEXT,
                not_found_reason TEXT,
                not_found_date DATE
            )
        ''')
        
        # Complaints table with all fields
        conn.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT,
                photo TEXT,
                description TEXT,
                marks TEXT,
                location TEXT,
                date DATE,
                status TEXT DEFAULT 'pending',
                reporter_name TEXT,
                relationship TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Search History table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT UNIQUE NOT NULL,
                person_name TEXT,
                person_age INTEGER,
                person_gender TEXT,
                photo_path TEXT,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'processing',
                progress INTEGER DEFAULT 0,
                total_videos INTEGER DEFAULT 0,
                results_count INTEGER DEFAULT 0,
                completed_at TIMESTAMP
            )
        ''')
        
        # Search Results table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id TEXT NOT NULL,
                video_file TEXT NOT NULL,
                timestamp TEXT,
                timestamp_seconds REAL,
                location TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(search_id) REFERENCES search_history(search_id)
            )
        ''')
        
        # Insert admin user if not exists
        admin_email = 'admin@facetrace.net'
        admin = conn.execute('SELECT * FROM users WHERE email = ?', (admin_email,)).fetchone()
        if not admin:
            conn.execute('''
                INSERT INTO users (name, email, password, phone)
                VALUES (?, ?, ?, ?)
            ''', ('Admin', admin_email, 'FaceTrace@123', '+0000000000'))
        conn.commit()

def update_cases_table():
    """Add new columns to cases table if they don't exist"""
    with get_db() as conn:
        # Check existing columns
        cursor = conn.execute("PRAGMA table_info(cases)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'found_location' not in existing_columns:
            try:
                conn.execute('ALTER TABLE cases ADD COLUMN found_location TEXT')
                print("Added found_location column")
            except sqlite3.OperationalError as e:
                print(f"Error adding found_location: {e}")
        
        if 'found_date' not in existing_columns:
            try:
                conn.execute('ALTER TABLE cases ADD COLUMN found_date DATE')
                print("Added found_date column")
            except sqlite3.OperationalError as e:
                print(f"Error adding found_date: {e}")
        
        if 'found_notes' not in existing_columns:
            try:
                conn.execute('ALTER TABLE cases ADD COLUMN found_notes TEXT')
                print("Added found_notes column")
            except sqlite3.OperationalError as e:
                print(f"Error adding found_notes: {e}")
        
        # Add new columns for not found status
        if 'not_found_reason' not in existing_columns:
            try:
                conn.execute('ALTER TABLE cases ADD COLUMN not_found_reason TEXT')
                print("Added not_found_reason column")
            except sqlite3.OperationalError as e:
                print(f"Error adding not_found_reason: {e}")
        
        if 'not_found_date' not in existing_columns:
            try:
                conn.execute('ALTER TABLE cases ADD COLUMN not_found_date DATE')
                print("Added not_found_date column")
            except sqlite3.OperationalError as e:
                print(f"Error adding not_found_date: {e}")
        
        # Add admin_notes to complaints table
        cursor = conn.execute("PRAGMA table_info(complaints)")
        complaint_columns = [column[1] for column in cursor.fetchall()]
        
        if 'admin_notes' not in complaint_columns:
            try:
                conn.execute('ALTER TABLE complaints ADD COLUMN admin_notes TEXT')
                print("Added admin_notes column to complaints")
            except sqlite3.OperationalError as e:
                print(f"Error adding admin_notes: {e}")
        
        conn.commit()
# Add this after init_db() and update_cases_table()
def debug_check_cases():
    """Debug function to check if cases exist in database"""
    try:
        with get_db() as conn:
            # Count cases
            count = conn.execute('SELECT COUNT(*) FROM cases').fetchone()[0]
            print(f"DEBUG: Total cases in database: {count}")
            
            # Show all cases
            cases = conn.execute('SELECT id, name, status, created_at FROM cases').fetchall()
            for case in cases:
                print(f"DEBUG: Case ID={case['id']}, Name={case['name']}, Status={case['status']}, Created={case['created_at']}")
            
            return count
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return 0

# Call this after database initialization
debug_check_cases()
# Initialize database
init_db()
update_cases_table()

# ==================== DECORATORS ====================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# ==================== location =========================
def get_location_from_csv(video_filename):
    import csv
    import os

    csv_path = os.path.join('data', 'cctv_locations.csv')

    if not os.path.exists(csv_path):
        print("CSV NOT FOUND")
        return "Unknown"

    video_filename = os.path.basename(video_filename).lower().strip()

    with open(csv_path, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            csv_video = os.path.basename(row['video_path']).lower().strip()

            # ✅ exact match
            if video_filename == csv_video:
                print("MATCH FOUND:", csv_video)
                return row['location_name']

    print("NO MATCH IN CSV")
    return "Unknown"
# ==================== FACE RECOGNITION FUNCTIONS ====================
def detect_face_opencv(image_path):
    """Detect face using OpenCV Haar Cascade"""
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    img = cv2.imread(image_path)
    if img is None:
        return None, None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(40, 40))
    
    if len(faces) == 0:
        return None, None
    
    (x, y, w, h) = faces[0]
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (100, 100))
    
    return face, (x, y, w, h)

def extract_face_features(face_image):
    """Extract LBP features from face"""
    radius = 1
    n_points = 8 * radius
    
    lbp = np.zeros_like(face_image)
    for i in range(radius, face_image.shape[0] - radius):
        for j in range(radius, face_image.shape[1] - radius):
            center = face_image[i, j]
            code = 0
            code |= (face_image[i - radius, j - radius] > center) << 7
            code |= (face_image[i - radius, j] > center) << 6
            code |= (face_image[i - radius, j + radius] > center) << 5
            code |= (face_image[i, j + radius] > center) << 4
            code |= (face_image[i + radius, j + radius] > center) << 3
            code |= (face_image[i + radius, j] > center) << 2
            code |= (face_image[i + radius, j - radius] > center) << 1
            code |= (face_image[i, j - radius] > center) << 0
            lbp[i, j] = code
    
    hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
    hist = hist.astype(np.float32)
    hist /= (hist.sum() + 1e-6)
    
    return hist

def compare_faces_opencv(face1, face2, threshold=0.75):
    """Compare two faces using multiple methods for better accuracy"""
    
    # Method 1: Histogram correlation
    features1 = extract_face_features(face1)
    features2 = extract_face_features(face2)
    hist_similarity = cv2.compareHist(features1, features2, cv2.HISTCMP_CORREL)
    hist_similarity = (hist_similarity + 1) / 2  # Normalize to 0-1
    
    # Method 2: Template matching
    # Resize face2 to match face1 size if needed
    if face2.shape != face1.shape:
        face2_resized = cv2.resize(face2, (face1.shape[1], face1.shape[0]))
    else:
        face2_resized = face2
    
    # Template matching
    result = cv2.matchTemplate(face1, face2_resized, cv2.TM_CCOEFF_NORMED)
    template_similarity = np.max(result)
    
    # Combine both methods (weighted average)
    combined_similarity = (hist_similarity * 0.6 + template_similarity * 0.4)
    
    return combined_similarity > threshold, combined_similarity

def preprocess_face(face_img):
    if len(face_img.shape) == 3:
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    face_img = cv2.resize(face_img, (100, 100))
    return face_img
def process_face_search_opencv(search_id, target_face, camera_filter=None):
    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        target_face = preprocess_face(target_face)

        video_files = [
            f for f in os.listdir(CCTV_FOLDER)
            if f.lower().endswith(('.mp4', '.avi', '.mov'))
        ]

        total_videos = len(video_files)
        matches_found_total = 0

        if total_videos == 0:
            print("ERROR: No videos found")
            return

        for video_file in video_files:
            video_path = os.path.join(CCTV_FOLDER, video_file)
            cap = cv2.VideoCapture(video_path)

            fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            clip_filename = f"{search_id}_{video_file.split('.')[0]}.mp4"
            clip_path = os.path.join('static/search_clips', clip_filename)

            out = cv2.VideoWriter(
                clip_path,
                fourcc,
                fps,
                (int(cap.get(3)), int(cap.get(4)))
            )

            pre_match_buffer = deque(maxlen=int(fps * 2))
            is_recording = False
            match_count = 0
            frames_to_record = int(fps * 6)
            count = 0
            match_time = None

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                count += 1

                if not is_recording:
                    pre_match_buffer.append(frame)

                # detect every 1 second
                if count % int(fps) == 0 and not is_recording:

                    small_frame = cv2.resize(frame, (0, 0), fx=0.7, fy=0.7)
                    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

                    faces = face_cascade.detectMultiScale(
                        gray, 1.2, 6, minSize=(50, 50)
                    )

                    for (x, y, w, h) in faces:
                        x, y, w, h = int(x/0.7), int(y/0.7), int(w/0.7), int(h/0.7)

                        roi = frame[y:y+h, x:x+w]

                        if roi is None or roi.size == 0:
                            continue

                        face_roi = cv2.resize(
                            cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),
                            (100, 100)
                        )

                        _, conf = compare_faces_opencv(
                            target_face,
                            preprocess_face(face_roi)
                        )

                        print("Confidence:", conf)

                        # MATCH CONDITION
                        if conf > 0.85:
                            match_count += 1

                            is_recording = True
                            match_time = str(
                                timedelta(seconds=int(count / fps))
                            )

                            for f in pre_match_buffer:
                                out.write(f)

                            pre_match_buffer.clear()

                            cv2.rectangle(
                                frame,
                                (x, y),
                                (x + w, y + h),
                                (0, 255, 0),
                                3
                            )

                            break
                        else:
                            match_count = 0

                # record matched clip
                if is_recording and match_time is not None:
                    out.write(frame)
                    frames_to_record -= 1

                    if frames_to_record <= 0:
                        break

            cap.release()
            out.release()

            # SAVE RESULT
            if is_recording and match_time is not None:
                with get_db() as conn:
                    conn.execute(
                        '''
                        INSERT INTO search_results 
                        (search_id, video_file, timestamp, location, confidence)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (
                            search_id,
                            clip_filename,
                            match_time,
                            get_location_from_csv(video_file),
                            0.65
                        )
                    )
                    conn.commit()

                matches_found_total += 1
                break

            else:
                if os.path.exists(clip_path):
                    os.remove(clip_path)

        print("TOTAL MATCHES:", matches_found_total)

        with get_db() as conn:
            if matches_found_total == 0:
                print("NO MATCH FOUND")
                conn.execute('''
                    UPDATE search_history 
                    SET status="completed", progress=100, results_count=0
                    WHERE search_id=?
                ''', (search_id,))
            else:
                conn.execute('''
                    UPDATE search_history 
                    SET status="completed", progress=100, results_count=?
                    WHERE search_id=?
                ''', (matches_found_total, search_id))

            conn.commit()

    except Exception as e:
        print("ERROR:", e)

# ==================== AUTHENTICATION ROUTES ====================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == 'admin@facetrace.net' and password == 'FaceTrace@123':
            session['user_id'] = 0
            session['role'] = 'admin'
            session['name'] = 'Admin'
            session['email'] = email
            return redirect(url_for('admin_dashboard'))

        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            if user and user['password'] == password:
                session['user_id'] = user['id']
                session['role'] = 'user'
                session['name'] = user['name']
                session['email'] = user['email']
                return redirect(url_for('user_dashboard'))
            else:
                flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']

        with get_db() as conn:
            try:
                conn.execute('''
                    INSERT INTO users (name, email, password, phone)
                    VALUES (?, ?, ?, ?)
                ''', (name, email, password, phone))
                conn.commit()
                flash('Registration successful. Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ==================== ADMIN ROUTES ====================
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    with get_db() as conn:
        total_missing = conn.execute('SELECT COUNT(*) FROM cases WHERE status="missing"').fetchone()[0]
        total_found = conn.execute('SELECT COUNT(*) FROM cases WHERE status="found"').fetchone()[0]
        total_not_found = conn.execute('SELECT COUNT(*) FROM cases WHERE status="not_found"').fetchone()[0]
        active_investigations = conn.execute('SELECT COUNT(*) FROM cases WHERE status="missing"').fetchone()[0]
    return render_template('admin/admin_dashboard.html',
                           total_missing=total_missing,
                           total_found=total_found,
                           total_not_found=total_not_found,
                           active_investigations=active_investigations)

@app.route('/admin/home')
@login_required
@admin_required
def admin_home():
    admin_actions = [
        {"title": "Missing Person Management", "description": "Add, edit, delete cases; view all reported cases.", "link": "/admin/add_case"},
        {"title": "Complaint Handling", "description": "Approve/reject complaints; track complaint status.", "link": "/admin/complaints_admin"},
        {"title": "CCTV Management", "description": "Upload, view, delete videos; search missing persons in CCTV footage.", "link": "/admin/cctv_gallery"},
        {"title": "User Access Control", "description": "Add/remove admins; set permissions.", "link": "#"},
        {"title": "Notifications/Alerts", "description": "Send alerts to authorities; broadcast emergency messages.", "link": "#"}
    ]
    return render_template('admin/admin_home.html', admin_actions=admin_actions)

@app.route('/admin/add_case', methods=['GET', 'POST'])
@login_required
@admin_required
def add_case():
    if request.method == 'POST':
        try:
            name = request.form['name']
            age = request.form['age']
            gender = request.form['gender']
            description = request.form['description']
            marks = request.form['marks']
            location = request.form['location']
            last_seen_date = request.form['last_seen_date']

            photo_file = request.files['photo']
            filename = None

            if photo_file and photo_file.filename != "":
                filename = secure_filename(photo_file.filename)
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, filename)
                photo_file.save(filepath)
                print(f"Photo saved at: {filepath}")  # Debug

            with get_db() as conn:
                cursor = conn.execute('''
                    INSERT INTO cases
                    (name, age, gender, photo, description, identifying_marks, last_seen_location, last_seen_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    name,
                    age if age else None,  # Handle empty age
                    gender,
                    filename,
                    description,
                    marks,
                    location,
                    last_seen_date,
                    'missing'
                ))
                conn.commit()
                
                # Debug: Print the inserted ID
                case_id = cursor.lastrowid
                print(f"Case inserted with ID: {case_id}")
                
                # Verify insertion by querying
                inserted = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
                print(f"Inserted case: {dict(inserted) if inserted else 'Not found'}")

            flash('Case added successfully.', 'success')
            return redirect(url_for('all_cases'))
            
        except Exception as e:
            print(f"Error adding case: {str(e)}")  # Debug
            flash(f'Error adding case: {str(e)}', 'danger')
            return redirect(request.url)
    
    return render_template('admin/add_case.html')

@app.route('/admin/all_cases')
@login_required
@admin_required
def all_cases():
    from datetime import datetime
    try:
        with get_db() as conn:
            # Debug: Print all cases
            rows = conn.execute('SELECT * FROM cases ORDER BY id DESC').fetchall()
            print(f"Found {len(rows)} cases in database")
            for row in rows:
                print(f"Case: {dict(row)}")
            
            # Get complaints with both complaint email and user email
            complaints = conn.execute('''
                SELECT complaints.*, 
                       users.name as user_name, 
                       users.email as user_email, 
                       users.phone as user_phone,
                       CASE 
                           WHEN complaints.email IS NOT NULL AND complaints.email != '' 
                           THEN complaints.email 
                           ELSE users.email 
                       END as reporter_email
                FROM complaints 
                LEFT JOIN users ON complaints.user_id = users.id 
                ORDER BY complaints.id DESC
            ''').fetchall()
        
        now = datetime.now()
        two_days_ago = now - timedelta(days=2)
        current_date = now.strftime('%Y-%m-%d')
        
        cases = []
        for row in rows:
            case = dict(row)
            if case['created_at']:
                try:
                    if isinstance(case['created_at'], str):
                        created = datetime.strptime(case['created_at'], '%Y-%m-%d %H:%M:%S')
                    else:
                        created = case['created_at']
                    case['is_new'] = created >= two_days_ago
                except Exception as e:
                    print(f"Error parsing date: {e}")
                    case['is_new'] = False
            cases.append(case)
        
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            # Use the reporter_email we created in the SQL query
            if complaint_dict.get('reporter_email'):
                complaint_dict['email'] = complaint_dict['reporter_email']
            # Fallback to complaint's own email if reporter_email is empty
            elif not complaint_dict.get('email'):
                complaint_dict['email'] = complaint_dict.get('user_email', '')
            
            if complaint_dict.get('created_at'):
                try:
                    if isinstance(complaint_dict['created_at'], str):
                        complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            complaints_list.append(complaint_dict)
        
        return render_template('admin/all_cases.html', cases=cases, complaints=complaints_list, current_date=current_date)
    
    except Exception as e:
        print(f"Error in all_cases: {str(e)}")
        flash(f'Error loading cases: {str(e)}', 'danger')
        return render_template('admin/all_cases.html', cases=[], complaints=[], current_date=datetime.now().strftime('%Y-%m-%d'))
@app.route('/admin/delete_case/<int:case_id>')
@login_required
@admin_required
def delete_case(case_id):
    with get_db() as conn:
        conn.execute('DELETE FROM cases WHERE id = ?', (case_id,))
        conn.commit()
    flash('Case deleted.', 'success')
    return redirect(url_for('all_cases'))

@app.route('/admin/view_person/<int:case_id>')
@login_required
@admin_required
def view_person_detail(case_id):
    with get_db() as conn:
        case = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()

    if not case:
        flash('Person not found.', 'danger')
        return redirect(url_for('all_cases'))
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/view_person_detail.html', case=case, current_date=current_date)






@app.route('/admin/register-case')
@login_required
@admin_required
def register_case():
    return render_template('admin/register_case.html')

@app.route('/admin/complaint_list')
@login_required
@admin_required
def complaint_list():
    with get_db() as conn:
        complaints = conn.execute('SELECT * FROM complaints ORDER BY id DESC').fetchall()
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
            complaints_list.append(complaint_dict)
    return render_template('admin/complaint_list.html', complaints=complaints_list)

@app.route('/admin/complaint/<int:complaint_id>')
@login_required
@admin_required
def complaint_detail(complaint_id):
    with get_db() as conn:
        complaint = conn.execute('''
            SELECT complaints.*, users.name as user_name 
            FROM complaints 
            LEFT JOIN users ON complaints.user_id = users.id 
            WHERE complaints.id=?
        ''', (complaint_id,)).fetchone()
        if complaint:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
            return render_template('admin/complaint_status.html', complaint=complaint_dict)
    return render_template('admin/complaint_status.html', complaint=None)

@app.route('/admin/complaints_admin')
@login_required
@admin_required
def complaints_admin():
    with get_db() as conn:
        complaints = conn.execute('''
            SELECT complaints.*, users.name as user_name
            FROM complaints 
            LEFT JOIN users ON complaints.user_id = users.id
            ORDER BY id DESC
        ''').fetchall()
        
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                try:
                    if isinstance(complaint_dict['created_at'], str):
                        complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            complaints_list.append(complaint_dict)
    
    return render_template('admin/complaints_admin.html', complaints=complaints_list)

@app.route('/admin/complaint-acceptance')
@login_required
@admin_required
def complaint_acceptance():
    with get_db() as conn:
        complaints = conn.execute("SELECT * FROM complaints WHERE status='pending' ORDER BY id DESC").fetchall()
        
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                try:
                    if isinstance(complaint_dict['created_at'], str):
                        complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            complaints_list.append(complaint_dict)
    
    return render_template('admin/complaint_acceptance.html', complaints=complaints_list)

@app.route('/admin/complaint-reject/<int:complaint_id>')
@login_required
@admin_required
def complaint_reject(complaint_id):
    with get_db() as conn:
        conn.execute("UPDATE complaints SET status='rejected' WHERE id=?", (complaint_id,))
        conn.commit()
    flash('Complaint rejected.', 'success')
    return redirect(url_for('complaint_acceptance'))

# ==================== UNIFIED COMPLAINTS MANAGEMENT ROUTES (AJAX) ====================

@app.route('/admin/accept_complaint/<int:complaint_id>', methods=['POST'])
@login_required
@admin_required
def accept_complaint_ajax(complaint_id):
    """Accept a complaint via AJAX"""
    try:
        with get_db() as conn:
            # Get complaint details
            complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
            
            if not complaint:
                return jsonify({'success': False, 'error': 'Complaint not found'})
            
            # Update complaint status
            conn.execute('UPDATE complaints SET status="accepted" WHERE id = ?', (complaint_id,))
            
            # Create case from complaint
            conn.execute('''
                INSERT INTO cases 
                (name, age, gender, photo, description, identifying_marks, 
                 last_seen_location, last_seen_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                complaint['name'],
                complaint['age'],
                complaint['gender'],
                complaint['photo'],
                complaint['description'],
                complaint['marks'],
                complaint['location'],
                complaint['date'],
                'missing'
            ))
            
            conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/reject_complaint/<int:complaint_id>', methods=['POST'])
@login_required
@admin_required
def reject_complaint_ajax(complaint_id):
    """Reject a complaint via AJAX"""
    try:
        with get_db() as conn:
            conn.execute('UPDATE complaints SET status="rejected" WHERE id = ?', (complaint_id,))
            conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/delete_complaint/<int:complaint_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_complaint_ajax(complaint_id):
    """Delete a complaint via AJAX"""
    try:
        with get_db() as conn:
            # Get complaint photo path
            complaint = conn.execute('SELECT photo FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
            
            # Delete the complaint
            conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
            conn.commit()
            
            # Delete photo if exists
            if complaint and complaint['photo']:
                photo_path = complaint['photo']
                if photo_path.startswith('uploads/'):
                    full_path = os.path.join('static', photo_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
@app.route('/admin/debug_complaint/<int:complaint_id>')
@login_required
@admin_required
def debug_complaint(complaint_id):
    """Debug route to check complaint photo path"""
    with get_db() as conn:
        complaint = conn.execute('SELECT id, name, photo FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        if complaint:
            # Check if file exists
            photo_path = complaint['photo']
            file_exists = False
            actual_path = None
            
            if photo_path:
                # Try different possible paths
                possible_paths = [
                    os.path.join('static', 'uploads', photo_path),
                    os.path.join('static', photo_path),
                    os.path.join('static', 'uploads', os.path.basename(photo_path)),
                    os.path.join('static', 'complaint_photos', os.path.basename(photo_path)),
                    os.path.join('static', 'uploads', photo_path.replace('uploads/', ''))
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        file_exists = True
                        actual_path = path
                        break
            
            return jsonify({
                'complaint_id': complaint['id'],
                'name': complaint['name'],
                'photo_path_in_db': photo_path,
                'file_exists': file_exists,
                'actual_path': actual_path,
                'possible_paths': possible_paths
            })
    
    return jsonify({'error': 'Complaint not found'}), 404



# Keep the original routes for backward compatibility (non-AJAX)
@app.route('/admin/accept_complaint_old/<int:complaint_id>')
@login_required
@admin_required
def accept_complaint_old(complaint_id):
    with get_db() as conn:
        conn.execute('UPDATE complaints SET status="accepted" WHERE id = ?', (complaint_id,))
        conn.commit()
    flash('Complaint accepted.', 'success')
    return redirect(url_for('complaints_admin'))

@app.route('/admin/reject_complaint_old/<int:complaint_id>')
@login_required
@admin_required
def reject_complaint_old(complaint_id):
    with get_db() as conn:
        conn.execute('UPDATE complaints SET status="rejected" WHERE id = ?', (complaint_id,))
        conn.commit()
    flash('Complaint rejected.', 'success')
    return redirect(url_for('complaints_admin'))

@app.route('/admin/delete_complaint_old/<int:complaint_id>')
@login_required
@admin_required
def delete_complaint_old(complaint_id):
    """Delete a complaint from the system"""
    try:
        with get_db() as conn:
            # Get complaint photo path to delete file if exists
            complaint = conn.execute('SELECT photo FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
            
            # Delete the complaint record
            conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
            conn.commit()
            
            # Delete the photo file if it exists
            if complaint and complaint['photo']:
                photo_path = complaint['photo']
                if photo_path.startswith('uploads/'):
                    full_path = os.path.join('static', photo_path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                        except:
                            pass  # Ignore file deletion errors
            
        flash('Complaint deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting complaint: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('all_cases'))

# ==================== MARK FOUND ROUTES (WITH EMAIL NOTIFICATION) ====================

@app.route('/admin/mark_found/<int:case_id>', methods=['POST'])
@login_required
@admin_required
def mark_found(case_id):
    found_location = request.form.get('found_location')
    found_date = request.form.get('found_date')
    found_notes = request.form.get('found_notes', '')
    send_email = request.form.get('send_email') == 'yes'
    
    with get_db() as conn:
        # Update the case
        conn.execute('''
            UPDATE cases 
            SET status='found', 
                found_location=?, 
                found_date=?, 
                found_notes=?
            WHERE id = ?
        ''', (found_location, found_date, found_notes, case_id))
        
        # Get case details to find related complaints
        case = conn.execute('SELECT name, photo, description FROM cases WHERE id = ?', (case_id,)).fetchone()
        
        # Update related complaints
        related_complaints = conn.execute('''
            SELECT * FROM complaints 
            WHERE name = ? AND (status = 'pending' OR status = 'accepted')
        ''', (case['name'],)).fetchall()
        
        for complaint in related_complaints:
            conn.execute('''
                UPDATE complaints 
                SET status='found', 
                    admin_notes=?
                WHERE id = ?
            ''', (f"Person was found at {found_location} on {found_date}. Notes: {found_notes}", complaint['id']))
            
            # Send email if enabled and email exists
            if send_email and complaint['email']:
                try:
                    send_found_notification_email(complaint['email'], complaint['reporter_name'], 
                                                complaint['name'], found_location, found_date, found_notes)
                    flash(f'Email notification sent to {complaint["email"]}', 'success')
                except Exception as e:
                    flash(f'Email failed for {complaint["email"]}: {str(e)}', 'warning')
        
        conn.commit()
    
    flash(f'Case marked as found at {found_location}.', 'success')
    return redirect(url_for('all_cases'))
@app.route('/admin/send_email_notification', methods=['POST'])
@login_required
@admin_required
def send_email_notification():
    """Send email notification to reporter"""
    try:
        data = request.get_json()
        email = data.get('email')
        person_name = data.get('person_name')
        reporter_name = data.get('reporter_name')
        message = data.get('message', '')
        
        if not email:
            return jsonify({'success': False, 'error': 'No email provided'})
        
        subject = f"Update on Missing Person: {person_name}"
        body = f"""
Dear {reporter_name or 'Sir/Madam'},

This is an update regarding the missing person case for {person_name}.

{message}

If you have any questions, please contact the authorities.

Best regards,
FaceTrace Team
"""
        
        # Create and send email
        msg = Message(subject, recipients=[email])
        msg.body = body
        
        try:
            mail.send(msg)
            print(f"✅ Email sent successfully to {email}")
            return jsonify({'success': True, 'message': 'Email sent successfully!'})
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            return jsonify({'success': False, 'error': f'Failed to send: {str(e)}'})
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
    

@app.route('/admin/mark_complaint_found/<int:complaint_id>', methods=['POST'])
@login_required
@admin_required
def mark_complaint_found(complaint_id):
    found_location = request.form.get('found_location')
    found_date = request.form.get('found_date')
    found_notes = request.form.get('found_notes', '')
    send_email = request.form.get('send_email') == 'yes'
    
    with get_db() as conn:
        # Update the complaint status
        conn.execute('''
            UPDATE complaints 
            SET status='found', 
                admin_notes=?
            WHERE id = ?
        ''', (f"Person was found at {found_location} on {found_date}. Notes: {found_notes}", complaint_id))
        
        # Get complaint details
        complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        # Check if there's an existing case for this person
        existing_case = conn.execute(
            'SELECT * FROM cases WHERE name = ? AND status = "missing"', 
            (complaint['name'],)
        ).fetchone()
        
        if existing_case:
            # Update the existing case
            conn.execute('''
                UPDATE cases 
                SET status='found', 
                    found_location=?, 
                    found_date=?, 
                    found_notes=?
                WHERE id = ?
            ''', (found_location, found_date, found_notes, existing_case['id']))
        else:
            # Create a new case with found status
            conn.execute('''
                INSERT INTO cases 
                (name, age, gender, photo, description, identifying_marks, 
                 last_seen_location, last_seen_date, status, found_location, found_date, found_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                complaint['name'],
                complaint['age'],
                complaint['gender'],
                complaint['photo'],
                complaint['description'],
                complaint['marks'],
                complaint['location'],
                complaint['date'],
                'found',
                found_location,
                found_date,
                found_notes
            ))
        
        conn.commit()
        
        # Send email notification if requested and email exists
        if send_email and complaint['email']:
            try:
                send_found_notification_email(complaint['email'], complaint['reporter_name'], 
                                            complaint['name'], found_location, found_date, found_notes)
                flash(f'Email notification sent to {complaint["email"]}', 'success')
            except Exception as e:
                flash(f'Complaint marked found but email failed: {str(e)}', 'warning')
    
    flash(f'{complaint["name"]} has been marked as found!', 'success')
    return redirect(url_for('all_cases'))

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_via_smtp(recipient_email, subject, body):
    """Send email using SMTP directly"""
    try:
        # Email configuration
        sender_email = "your_email@gmail.com"  # Your email
        sender_password = "your_app_password"   # Your app password
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

    
@app.route('/admin/mark_not_found/<int:case_id>', methods=['POST'])
@login_required
@admin_required
def mark_not_found(case_id):
    not_found_reason = request.form.get('not_found_reason', '')
    not_found_date = request.form.get('not_found_date')
    
    with get_db() as conn:
        conn.execute('''
            UPDATE cases 
            SET status='not_found', 
                not_found_reason=?, 
                not_found_date=?
            WHERE id = ?
        ''', (not_found_reason, not_found_date, case_id))
        
        # Update related complaints
        case = conn.execute('SELECT name FROM cases WHERE id = ?', (case_id,)).fetchone()
        conn.execute('''
            UPDATE complaints 
            SET status='not_found', 
                admin_notes=?
            WHERE name = ? AND status = 'accepted'
        ''', (f"Case closed as not found on {not_found_date}. Reason: {not_found_reason}", case['name']))
        conn.commit()
    
    flash(f'Case marked as NOT FOUND.', 'info')
    return redirect(url_for('all_cases'))

# ==================== EDIT ROUTES ====================

# Edit Case Route
@app.route('/admin/edit_case/<int:case_id>', methods=['POST'])
@login_required
@admin_required
def edit_case(case_id):
    try:
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        location = request.form.get('location')
        date = request.form.get('date')
        description = request.form.get('description')
        marks = request.form.get('marks')
        
        with get_db() as conn:
            conn.execute('''
                UPDATE cases 
                SET name=?, age=?, gender=?, last_seen_location=?, last_seen_date=?, 
                    description=?, identifying_marks=?
                WHERE id=?
            ''', (name, age, gender, location, date, description, marks, case_id))
            conn.commit()
        
        flash('Case updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating case: {str(e)}', 'danger')
    
    return redirect(url_for('all_cases'))

# Edit Complaint Route
@app.route('/admin/edit_complaint/<int:complaint_id>', methods=['POST'])
@login_required
@admin_required
def edit_complaint(complaint_id):
    try:
        # Missing person info
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        location = request.form.get('location')
        date = request.form.get('date')
        description = request.form.get('description')
        marks = request.form.get('marks')
        
        # Reporter info
        reporter_name = request.form.get('reporter_name')
        relationship = request.form.get('relationship')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        
        with get_db() as conn:
            conn.execute('''
                UPDATE complaints 
                SET name=?, age=?, gender=?, location=?, date=?, 
                    description=?, marks=?, reporter_name=?, relationship=?, 
                    phone=?, email=?, address=?
                WHERE id=?
            ''', (name, age, gender, location, date, description, marks, 
                  reporter_name, relationship, phone, email, address, complaint_id))
            conn.commit()
        
        flash('Complaint updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating complaint: {str(e)}', 'danger')
    
    return redirect(url_for('all_cases'))

# ==================== EMAIL CONFIGURATION ====================

# Helper function to send email notification (fallback version - prints instead of sending)
def send_found_notification_email(recipient_email, reporter_name, person_name, found_location, found_date, notes):
    """Send email notification when a missing person is found (prints to console)"""
    subject = f"Good News! {person_name} Has Been Found"
    
    body = f"""
Dear {reporter_name or 'Sir/Madam'},

We are pleased to inform you that {person_name} has been found safe!

Details:
- Location Found: {found_location}
- Date Found: {found_date}
- Additional Notes: {notes}

Thank you for your cooperation and patience throughout this process.

Best regards,
FaceTrace Team
"""
    
    # Print email details to console (for now)
    print("\n" + "="*50)
    print(f"EMAIL WOULD BE SENT TO: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print("="*50 + "\n")
    
    return True
@app.route('/admin/complaint_detail/admin_edit_person/<int:complaint_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_complaint(complaint_id):
    with get_db() as conn:
        if request.method == 'POST':
            name = request.form['name']
            age = request.form['age']
            location = request.form['location']
            date = request.form['date']
            description = request.form.get('description')
            marks = request.form.get('marks')
            
            photo_file = request.files.get('photo')
            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, filename)
                photo_file.save(filepath)
                photo_path = 'uploads/' + filename
                
                conn.execute('''
                    UPDATE complaints 
                    SET name=?, age=?, location=?, date=?, description=?, marks=?, photo=?
                    WHERE id=?
                ''', (name, age, location, date, description, marks, photo_path, complaint_id))
            else:
                conn.execute('''
                    UPDATE complaints 
                    SET name=?, age=?, location=?, date=?, description=?, marks=?
                    WHERE id=?
                ''', (name, age, location, date, description, marks, complaint_id))
            
            conn.commit()
            flash('Complaint updated successfully.', 'success')
            return redirect(url_for('complaint_detail', complaint_id=complaint_id))
        
        complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        if not complaint:
            flash('Complaint not found.', 'danger')
            return redirect(url_for('complaint_list'))
        
        complaint_dict = dict(complaint)
        if complaint_dict.get('created_at'):
            complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
        
        return render_template('admin/admin_edit_person.html', complaint=complaint_dict)

@app.route('/admin/cctv-gallery')
@login_required
@admin_required
def cctv_gallery():
    folder_path = 'static/videos'
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    
    video_files = []

    if os.path.exists(folder_path):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            
            if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                file_stat = os.stat(file_path)
                
                upload_date = None
                if file.startswith('20') and len(file) > 15:
                    try:
                        date_str = file[:15]
                        upload_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    except:
                        upload_date = datetime.fromtimestamp(file_stat.st_mtime)
                else:
                    upload_date = datetime.fromtimestamp(file_stat.st_mtime)
                
                video_files.append({
                    "name": file,
                    "path": file_path.replace('\\', '/'),
                    "size": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "upload_date": upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "extension": file.rsplit('.', 1)[1].lower() if '.' in file else 'unknown'
                })
    
    video_files.sort(key=lambda x: x['upload_date'], reverse=True)
    
    return render_template('admin/cctv_gallery.html', videos=video_files)

@app.route('/admin/cctv_upload', methods=['GET', 'POST'])
@login_required
@admin_required
def cctv_upload():
    if request.method == 'POST':
        if 'video' not in request.files:
            flash('No video file selected', 'error')
            return redirect(request.url)
        
        file = request.files['video']
        
        if file.filename == '':
            flash('No video file selected', 'error')
            return redirect(request.url)
        
        ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}
        
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            camera_id = request.form.get('camera_id')  # e.g. cam001
            filename = (camera_id or "default_camera") + ".mp4"
            
            upload_folder = os.path.join('static', 'videos')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            
            camera_location = request.form.get('camera_location', 'Unknown')
            custom_location = request.form.get('custom_location', '')
            
            flash(f'Video uploaded successfully!', 'success')
            return redirect(url_for('cctv_gallery'))
        else:
            flash('Invalid file type. Please upload a video file.', 'error')
            return redirect(request.url)
    
    return render_template('admin/cctv_upload.html')

@app.route('/admin/delete-video/<video_name>', methods=['POST'])
def delete_video(video_name):
    try:
        file_path = os.path.join(CCTV_FOLDER, video_name)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'File does not exist.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/admin/rename-video', methods=['POST'])
def rename_video():
    try:
        data = request.get_json()
        old_name = data.get('old_name')
        new_name = data.get('new_name')

        old_path = os.path.join(CCTV_FOLDER, old_name)

        # ensure .mp4
        if not new_name.endswith('.mp4'):
            new_name += '.mp4'

        new_path = os.path.join(CCTV_FOLDER, new_name)

        if not os.path.exists(old_path):
            return jsonify({'success': False, 'error': 'File not found'})

        os.rename(old_path, new_path)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    

@app.route('/admin/search-person', methods=['GET', 'POST'])
@login_required
@admin_required
def search_person():
    """Page to upload a person's photo for searching in CCTV"""
    if request.method == 'POST':
        person_name = request.form.get('name', '')
        person_age = request.form.get('age', '')
        person_gender = request.form.get('gender', '')
        marks = request.form.get('marks', '')
        camera_location = request.form.get('camera_location', '')
        
        if 'photo' not in request.files:
            flash('No photo uploaded', 'error')
            return redirect(request.url)
        
        photo = request.files['photo']
        
        if photo.filename == '':
            flash('No photo selected', 'error')
            return redirect(request.url)
        
        ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' in photo.filename and photo.filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = secure_filename(f"search_{timestamp}_{photo.filename}")
            photo_path = os.path.join('static/uploads', filename)
            photo.save(photo_path)
            
            target_face, face_location = detect_face_opencv(photo_path)
            
            if target_face is None:
                flash('No face detected in the uploaded photo. Please try another photo.', 'error')
                return redirect(request.url)
            
            face_filename = f"face_{timestamp}.jpg"
            face_path = os.path.join('static/search_results', face_filename)
            cv2.imwrite(face_path, target_face)
            
            search_id = f"search_{timestamp}"
            
            with get_db() as conn:
                conn.execute('''
                    INSERT INTO search_history (search_id, person_name, person_age, person_gender, photo_path, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (search_id, person_name, person_age, person_gender, photo_path, 'processing'))
                conn.commit()
            
            thread = threading.Thread(target=process_face_search_opencv, args=(search_id, target_face, camera_location))
            thread.daemon = True
            thread.start()
            
            flash('Search started! You will be redirected to results page.', 'success')
            return redirect(url_for('search_results', search_id=search_id))
        else:
            flash('Invalid file type. Please upload an image.', 'error')
            return redirect(request.url)
    
    return render_template('admin/search_person.html')

@app.route('/admin/search_results/')
@app.route('/admin/search_results/<search_id>')
@login_required
@admin_required
def search_results(search_id=None):
    if search_id is None:
        with get_db() as conn:
            searches = conn.execute('SELECT * FROM search_history').fetchall()
        return render_template('admin/all_searches.html', searches=searches)

    with get_db() as conn:
        search = conn.execute(
            'SELECT * FROM search_history WHERE search_id = ?', 
            (search_id,)
        ).fetchone()

        results = conn.execute(
            'SELECT * FROM search_results WHERE search_id = ?', 
            (search_id,)
        ).fetchall()

    if not search:
        return abort(404)

    results_list = []
    for result in results:
        res = dict(result)
        res['clip_path'] = url_for('serve_video', filename=res['video_file'])
        results_list.append(res)

    return render_template(
        'admin/search_results.html',
        search=search,
        results=results_list
    )

@app.route('/admin/search-status/<search_id>')
@login_required
@admin_required
def search_status(search_id):
    with get_db() as conn:
        search = conn.execute('SELECT * FROM search_history WHERE search_id = ?', (search_id,)).fetchone()
        results_count = conn.execute('SELECT COUNT(*) FROM search_results WHERE search_id = ?', (search_id,)).fetchone()[0]
    
    if search:
        return jsonify({
            'status': search['status'],
            'progress': search['progress'] if 'progress' in search.keys() else 0,
            'results_count': results_count,
            'total_videos': search['total_videos'] if 'total_videos' in search.keys() else 0
        })
    return jsonify({'status': 'not_found'})

@app.route('/admin/search-history')
@login_required
@admin_required
def search_history():
    with get_db() as conn:
        searches = conn.execute('''
            SELECT * FROM search_history 
            ORDER BY search_date DESC
        ''').fetchall()
    
    return render_template('admin/search_history.html', searches=searches)

@app.route('/admin/match_cases')
@login_required
@admin_required
def admin_match_cases():
    return render_template('admin/match_cases.html')

@app.route('/admin/search', methods=['GET', 'POST'])
@login_required
@admin_required
def search():
    results = []
    if request.method == 'POST':
        query = request.form['query']
        with get_db() as conn:
            results = conn.execute('''
                SELECT * FROM cases
                WHERE name LIKE ? OR description LIKE ? OR last_seen_location LIKE ?
            ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
    return render_template('admin/search_person.html', results=results)

@app.route('/admin/search_results_images/<filename>')
@login_required
@admin_required
def serve_search_image(filename):
    file_path = os.path.join('static', 'search_results', filename)
    if not os.path.exists(file_path):
        return abort(404)
    return send_file(file_path, mimetype='image/jpeg')

@app.route('/admin/search_results', methods=['GET', 'POST'])
@login_required
@admin_required
def result():
    results = []
    person_name = request.form.get('name')
    if person_name:
        person_name = person_name.lower()
        matched_persons = [
            {"name": "John Doe", "location": "Bus Stand", "image": "john_doe1.jpg"},
            {"name": "Jane Smith", "location": "Market Area", "image": "jane_smith1.jpg"}
        ]
        for person in matched_persons:
            if person_name in person['name'].lower():
                results.append(person)
    return render_template('admin/search_results.html', results=results)

# ==================== SEARCH FROM COMPLAINT ROUTES ====================
@app.route('/admin/search_from_complaint/<int:complaint_id>', methods=['POST'])
@login_required
@admin_required
def search_from_complaint(complaint_id):
    """Use complaint photo to search in CCTV footage"""
    with get_db() as conn:
        complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        if not complaint:
            flash('Complaint not found.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        if not complaint['photo']:
            flash('No photo available for this complaint.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Get the photo path
        photo_path = complaint['photo']
        
        # Handle different path formats
        if photo_path.startswith('uploads/'):
            filename = photo_path.replace('uploads/', '')
        else:
            filename = photo_path
        
        full_photo_path = os.path.join('static', 'uploads', filename)
        
        if not os.path.exists(full_photo_path):
            flash('Photo file not found on server.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Get person details from form or complaint
        person_name = request.form.get('name', complaint['name'])
        person_age = request.form.get('age', complaint['age'])
        person_gender = request.form.get('gender', complaint['gender'])
        
        # Detect face in the photo
        target_face, face_location = detect_face_opencv(full_photo_path)
        
        if target_face is None:
            flash('No face detected in the uploaded photo. Please try another photo.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Create search ID and record
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        search_id = f"search_{timestamp}"
        
        # Save face image for reference
        face_filename = f"face_{timestamp}.jpg"
        face_path = os.path.join('static/search_results', face_filename)
        cv2.imwrite(face_path, target_face)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO search_history (search_id, person_name, person_age, person_gender, photo_path, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (search_id, person_name, person_age, person_gender, full_photo_path, 'processing'))
            conn.commit()
        
        # Start search in background
        camera_location = f"From Complaint: {complaint['location']}"
        thread = threading.Thread(target=process_face_search_opencv, args=(search_id, target_face, camera_location))
        thread.daemon = True
        thread.start()
        
        flash(f'Search started for {person_name}! You will be redirected to results page.', 'success')
        return redirect(url_for('search_results', search_id=search_id))

@app.route('/admin/search_from_complaint_direct/<int:complaint_id>')
@login_required
@admin_required
def search_from_complaint_direct(complaint_id):
    """Use complaint photo to search in CCTV footage - Direct link"""
    with get_db() as conn:
        complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        if not complaint:
            flash('Complaint not found.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        if not complaint['photo']:
            flash('No photo available for this complaint.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Get the photo path
        photo_path = complaint['photo']
        
        # Handle different path formats
        if photo_path.startswith('uploads/'):
            filename = photo_path.replace('uploads/', '')
        else:
            filename = photo_path
        
        full_photo_path = os.path.join('static', 'uploads', filename)
        
        if not os.path.exists(full_photo_path):
            flash('Photo file not found on server.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Get person details from complaint
        person_name = complaint['name']
        person_age = complaint['age']
        person_gender = complaint['gender']
        
        # Detect face in the photo
        target_face, face_location = detect_face_opencv(full_photo_path)
        
        if target_face is None:
            flash('No face detected in the uploaded photo. Please try another photo.', 'danger')
            return redirect(url_for('complaints_admin'))
        
        # Create search ID and record
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        search_id = f"search_{timestamp}"
        
        # Save face image for reference
        face_filename = f"face_{timestamp}.jpg"
        face_path = os.path.join('static/search_results', face_filename)
        cv2.imwrite(face_path, target_face)
        
        # Save original photo copy for reference
        import shutil
        original_copy = os.path.join('static/search_results', f"original_{timestamp}_{filename}")
        shutil.copy2(full_photo_path, original_copy)
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO search_history (search_id, person_name, person_age, person_gender, photo_path, status, total_videos)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (search_id, person_name, person_age, person_gender, full_photo_path, 'processing', 0))
            conn.commit()
        
        # Start search in background
        camera_location = f"From Complaint: {complaint['location']}"
        thread = threading.Thread(target=process_face_search_opencv, args=(search_id, target_face, camera_location))
        thread.daemon = True
        thread.start()
        
        flash(f'Search started for {person_name}! The system will search through all CCTV footage.', 'success')
        return redirect(url_for('search_results', search_id=search_id))

@app.route('/admin/download_complaint_photo/<int:complaint_id>')
@login_required
@admin_required
def download_complaint_photo(complaint_id):
    """Download the photo from a complaint"""
    with get_db() as conn:
        complaint = conn.execute('SELECT photo, name FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        
        if not complaint or not complaint['photo']:
            flash('No photo found for this complaint.', 'danger')
            return redirect(request.referrer or url_for('complaints_admin'))
        
        # Get the photo path
        photo_path = complaint['photo']
        
        # Handle different path formats
        if photo_path.startswith('uploads/'):
            filename = photo_path.replace('uploads/', '')
        else:
            filename = photo_path
        
        file_path = os.path.join('static', 'uploads', filename)
        
        if os.path.exists(file_path):
            # Send file as attachment with person's name
            person_name = complaint['name'].replace(' ', '_')
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"{person_name}_photo.jpg",
                mimetype='image/jpeg'
            )
        else:
            flash('Photo file not found on server.', 'danger')
            return redirect(request.referrer or url_for('complaints_admin'))
@app.route('/admin/debug_cases')
@login_required
@admin_required
def debug_cases():
    """Debug route to check cases"""
    with get_db() as conn:
        cases = conn.execute('SELECT * FROM cases ORDER BY id DESC').fetchall()
        
        result = {
            'total': len(cases),
            'cases': []
        }
        
        for case in cases:
            result['cases'].append({
                'id': case['id'],
                'name': case['name'],
                'status': case['status'],
                'created_at': case['created_at']
            })
        
        return jsonify(result)

# ==================== USER ROUTES ====================
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    with get_db() as conn:
        total_missing = conn.execute('SELECT COUNT(*) FROM cases WHERE status="missing"').fetchone()[0]
        total_found = conn.execute('SELECT COUNT(*) FROM cases WHERE status="found"').fetchone()[0]
     
        active_investigations = conn.execute('SELECT COUNT(*) FROM cases WHERE status="missing"').fetchone()[0]
    return render_template('user/user_dashboard.html',
                           total_missing=total_missing,
                           total_found=total_found,
                           active_investigations=active_investigations)
    
@app.route('/user/register_complaint', methods=['GET', 'POST'])
def register_complaint():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        location = request.form['location']
        date = request.form['date']
        
        description = request.form.get('description', '')
        marks = request.form.get('marks', '')
        
        reporter_name = request.form.get('reporter_name', '')
        relationship = request.form.get('relationship', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')  # Get email from form
        address = request.form.get('address', '')

        photo_file = request.files.get('photo')
        photo_db_path = None

        # Make photo optional - only save if provided
        if photo_file and photo_file.filename != "":
            original_filename = photo_file.filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"complaint_{timestamp}_{secure_filename(original_filename)}"
            
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            photo_file.save(filepath)
            
            photo_db_path = 'uploads/' + filename
            print(f"Photo saved for complaint: {filepath}")

        with get_db() as conn:
            user_id = session.get('user_id')
            
            # If user is logged in but didn't provide email, get it from users table
            if user_id and not email:
                user = conn.execute('SELECT email FROM users WHERE id = ?', (user_id,)).fetchone()
                if user and user['email']:
                    email = user['email']
                    print(f"Using logged-in user's email: {email}")
            
            # If still no email, use a default or leave empty
            if not email:
                email = None
                print("No email provided for complaint")
            
            conn.execute('''
                INSERT INTO complaints (
                    user_id, name, age, gender, photo, description, marks, 
                    location, date, status, reporter_name, relationship, 
                    phone, email, address
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                name,
                age,
                gender,
                photo_db_path,
                description,
                marks,
                location,
                date,
                'pending',
                reporter_name,
                relationship,
                phone,
                email,
                address
            ))
            conn.commit()
            
            print(f"Complaint registered for: {name} with email: {email}")

        flash('Complaint registered successfully! It will be reviewed by admin.', 'success')
        return redirect(url_for('complaint_status'))

    return render_template('user/complaints_user.html')

@app.route('/user/complaint_status')
@login_required
def complaint_status():
    with get_db() as conn:
        complaints = conn.execute('SELECT * FROM complaints WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        # Convert created_at strings to datetime objects
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                try:
                    if isinstance(complaint_dict['created_at'], str):
                        complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            complaints_list.append(complaint_dict)
            
    return render_template('user/complaint_status.html', complaints=complaints_list)

@app.route('/user/history')
@login_required
def history():
    with get_db() as conn:
        complaints = conn.execute('SELECT * FROM complaints WHERE user_id = ? ORDER BY id DESC', (session['user_id'],)).fetchall()
        # Convert created_at strings to datetime objects
        complaints_list = []
        for complaint in complaints:
            complaint_dict = dict(complaint)
            if complaint_dict.get('created_at'):
                try:
                    if isinstance(complaint_dict['created_at'], str):
                        complaint_dict['created_at'] = datetime.strptime(complaint_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                except:
                    pass
            complaints_list.append(complaint_dict)
    return render_template('user/complaint_status.html', complaints=complaints_list)

# ==================== SHARED ROUTES ====================
@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    role = session['role']
    if role == 'admin':
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (session['email'],)).fetchone()
        return render_template('profile.html', user=user, role=role)
    else:
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            conn.execute('UPDATE users SET name=?, phone=? WHERE id=?', (name, phone, user_id))
            conn.commit()
            session['name'] = name
            flash('Profile updated.', 'success')
            return redirect(url_for('profile'))
        return render_template('user/profile.html', user=user, role=role)

@app.route('/user/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/user/help')
@login_required
def help():
    return render_template('user/help.html')

# ==================== VIDEO STREAMING ROUTE ====================
@app.route('/admin/video/<path:filename>')
def serve_video(filename):

    # 🔥 FIRST check matched clips
    file_path = os.path.join('static', 'search_clips', filename)

    # 🔄 If not found, check CCTV videos
    if not os.path.exists(file_path):
        file_path = os.path.join('static', 'videos', filename)

    # ❌ If still not found
    if not os.path.exists(file_path):
        return abort(404)

    return send_file(
        file_path,
        mimetype='video/mp4',
        conditional=True
    )

# ==================== MISC ROUTES ====================
@app.route("/")
def home():
    return redirect(url_for('login'))

@app.route("/search", methods=["POST"])
def search_route():
    from face_matcher import find_match
    
    file = request.files["photo"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    match_image = find_match(filepath, VIDEO_PATH)

    results = []

    if match_image:
        results.append({
            "name": "Missing Person",
            "location": "CCTV Camera",
            "match_score": 85,
            "uploaded_image": "uploads/" + file.filename,
            "result_image": "matches/match.jpg"
        })

    return render_template("match_case.html", results=results)

# ==================== APP CONFIGURATION ====================
UPLOAD_FOLDER = "static/uploads"
VIDEO_PATH = "videps/sample.mp4"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True) 