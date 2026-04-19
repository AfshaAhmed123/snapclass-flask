# SnapClass AI — Flask Edition
**Built by Afsha Ahmed**

Full-stack Flask conversion of the SnapClass AI Attendance System.
Face Recognition + Voice Biometrics + Parent Email Alerts.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your credentials
# Edit the .env file with your Supabase URL and Key

# 3. Run
python app.py

# 4. Open in browser
http://localhost:5002
```

---

## 📁 Project Structure

```
snapclass-flask/
├── app.py                  ← Main Flask app + all routes
├── requirements.txt
├── vercel.json             ← Vercel deployment config
├── .env                    ← Your credentials (never commit this)
├── src/
│   ├── database/
│   │   ├── config.py       ← Supabase client
│   │   └── db.py           ← All database functions
│   ├── pipelines/
│   │   ├── face_pipeline.py  ← Face recognition AI
│   │   └── voice_pipeline.py ← Voice recognition AI
│   └── utils/
│       └── email_utils.py  ← Parent email alerts
├── templates/
│   ├── base.html           ← Base layout
│   ├── home.html           ← Home screen
│   ├── teacher_login.html  ← Teacher login/register
│   ├── teacher_dashboard.html ← Full teacher dashboard
│   ├── student_login.html  ← Student FaceID login
│   └── student_dashboard.html ← Student portal
└── static/
    ├── css/style.css       ← All styles
    └── js/main.js          ← Global JS
```

---

## 🔑 Login Flow

### Teacher
1. Go to `/teacher`
2. Click **Register** → create your account
3. Login with username + password

**Demo credentials (after registering):**
- Username: `afsha123`
- Password: `Admin@123`

### Student
1. Go to `/student`
2. Camera opens automatically
3. Click **Scan My Face**
4. If not recognized → Register with name + optional voice

---

## 🗄️ Supabase Setup

Create these tables in your Supabase project:

```sql
-- Teachers
create table teachers (
  teacher_id uuid default gen_random_uuid() primary key,
  username text unique not null,
  password text not null,
  name text not null
);

-- Students
create table students (
  student_id serial primary key,
  name text not null,
  face_embedding jsonb,
  voice_embedding jsonb
);

-- Subjects
create table subjects (
  subject_id uuid default gen_random_uuid() primary key,
  subject_code text unique not null,
  name text not null,
  section text not null,
  teacher_id uuid references teachers(teacher_id)
);

-- Enrollments
create table subject_students (
  id serial primary key,
  student_id int references students(student_id),
  subject_id uuid references subjects(subject_id)
);

-- Attendance Logs
create table attendance_logs (
  id serial primary key,
  student_id int references students(student_id),
  subject_id uuid references subjects(subject_id),
  timestamp text,
  is_present boolean
);
```

---

## 📧 Parent Email Alerts

When teacher confirms attendance, absent students' parents get emailed automatically.

**Demo mode** (default): logs the alert in UI
**Real emails**: fill SMTP details in `.env`

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_app_password   ← generate at myaccount.google.com/apppasswords
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Home screen |
| GET | /teacher | Teacher login |
| GET | /student | Student FaceID login |
| GET | /teacher/dashboard | Teacher dashboard |
| GET | /student/dashboard | Student dashboard |
| POST | /api/teacher/login | Teacher login |
| POST | /api/teacher/register | Teacher register |
| GET | /api/subjects | Get teacher's subjects |
| POST | /api/subjects/create | Create new subject |
| GET | /api/subjects/<id>/qr | Get QR code for subject |
| POST | /api/attendance/face | Run face attendance |
| POST | /api/attendance/voice | Run voice attendance |
| POST | /api/attendance/confirm | Save + send email alerts |
| GET | /api/attendance/records | Get attendance records |
| POST | /api/student/face-login | Student face login |
| POST | /api/student/register | Register new student |
| POST | /api/student/enroll | Enroll in subject |
| POST | /api/student/unenroll | Unenroll from subject |

---

## ☁️ Deploy to Vercel

```bash
npm i -g vercel
vercel
```

Set environment variables in Vercel dashboard:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SECRET_KEY`

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Face AI | face_recognition, dlib |
| Voice AI | Resemblyzer, Librosa |
| Database | Supabase (PostgreSQL) |
| Auth | bcrypt + Flask sessions |
| QR Codes | segno |
| Deploy | Vercel / any Python host |

---

© 2026 SnapClass AI · Built by Afsha Ahmed
