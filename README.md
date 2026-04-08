# FaceTrace – Missing Person Detection System

AI-powered system that identifies missing persons by analyzing CCTV footage using computer vision techniques.

---

## Overview

FaceTrace is a computer vision based system designed to help identify missing persons by analyzing CCTV video footage. The system allows users to register missing person details and upload CCTV videos. It then detects faces in the video frames and compares them with stored images to find potential matches.

The system processes CCTV footage by extracting video frames, detecting faces using OpenCV, and comparing them with registered missing person images to identify potential matches.

This project aims to assist authorities and organizations in locating missing individuals more efficiently using automated surveillance analysis.

---
## Academic Context

This project was developed as part of my **B.Tech Final Year Project in Computer Science and Engineering**.
The objective of this project is to explore how **computer vision and AI techniques** can assist in identifying missing persons by analyzing CCTV surveillance footage and detecting potential facial matches.

---

## Features

-  User registration and login system
-  Missing person registration
-  CCTV video upload and processing
-  Face detection using OpenCV
-  Face comparison and matching
-  Admin dashboard for monitoring
-  Search history tracking

---

## Technologies Used

- Python
- Flask
- OpenCV
- NumPy
- SQLite
- HTML
- CSS
- JavaScript

---

## Project Structure

```
facetrace-missing-person-detection
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── ...
│
├── static
│   ├── css
│   ├── js
│   └── images
│
├── utils
│   └── database.py
│
├── uploads
│
└── screenshots
    ├── admin
    │   ├── admin_login.jpg
    │   ├── admin_dashboard.jpg
    │   ├── admin_add_case.jpg
    │   ├── admin_upload_cctv.jpg
    │   ├── admin_search_person.jpg
    │   └── admin_search_result.jpg
    │
    └── user
        ├── user_home.jpg
        └── user_complaint_form.jpg
```

---

## System Interface

### Admin Panel

**Admin Login**

![Admin Login](screenshots/admin/admin_login.jpg)

---

**Admin Dashboard**

![Admin Dashboard](screenshots/admin/admin_dashboard.jpg)

---

**Add Missing Person Case**

![Add Case](screenshots/admin/admin_add_case.jpg)

---

**Upload CCTV Footage**

![Upload CCTV](screenshots/admin/admin_upload_cctv.jpg)

---

**Search Missing Person**

![Search Person](screenshots/admin/admin_search_person.jpg)

---

**Search Result**

![Search Result](screenshots/admin/admin_search_result.jpg)

---

### User Panel

**User Home Page**

![User Home](screenshots/user/user_home.jpg)

---

**User Complaint Form**

![User Complaint](screenshots/user/user_complaint_form.jpg)

---

## Installation

Clone the repository

```
git clone https://github.com/swetha-sivadharshini/facetrace-missing-person-detection.git
```

Navigate to project folder

```
cd facetrace-missing-person-detection
```

Install dependencies

```
pip install -r requirements.txt
```

Run the application

```
python app.py
```

Open the browser and visit

```
http://127.0.0.1:5000
```

---

## Future Improvements

- Integration with deep learning face recognition models
- Real-time CCTV camera integration
- Cloud deployment
- Mobile application support
---

## Author

**Swetha Sivadharshini R**

B.Tech – Computer Science and Engineering

Final Year Project (2026)

