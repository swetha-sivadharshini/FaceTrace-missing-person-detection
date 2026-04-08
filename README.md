# FaceTrace – Missing Person Detection System

An AI-powered system that identifies missing persons by analyzing CCTV footage using computer vision techniques.

---

# Overview

FaceTrace is a computer vision based application designed to assist authorities in locating missing persons using surveillance footage.
The system allows users to register missing person cases and upload CCTV video recordings. It then detects faces in the video frames and compares them with stored images to identify possible matches.

By automating the process of scanning large volumes of CCTV footage, FaceTrace helps reduce manual effort and speeds up investigations.

---

# Features

• User registration and login system
• Missing person case registration
• CCTV video upload and processing
• Face detection using OpenCV
• Face comparison and matching
• Admin dashboard for monitoring cases
• Complaint management system
• Search history tracking

---

# Technologies Used

Backend
• Python
• Flask

AI / Computer Vision
• OpenCV
• NumPy

Database
• SQLite

Frontend
• HTML
• CSS
• JavaScript

---

# Project Structure

```
FACETRACE
│
├── ai/                     # Face detection and video processing modules
├── data/                   # CCTV location data
├── static/                 # CSS, JavaScript, and assets
├── templates/              # HTML templates for UI
├── utils/                  # Database helper functions
│
├── FaceTrace.db            # SQLite database
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── LICENSE                 # License file
```

---

# Installation

### 1 Clone the repository

```
git clone https://github.com/swetha-sivadharshini/facetrace-missing-person-detection.git
```

### 2 Navigate to the project directory

```
cd facetrace-missing-person-detection
```

### 3 Install dependencies

```
pip install -r requirements.txt
```

### 4 Run the application

```
python app.py
```

### 5 Open the browser

```
http://127.0.0.1:5000
```

---

# Future Improvements

• Integration with deep learning face recognition models
• Real-time CCTV camera integration
• Cloud deployment
• Mobile application support
• Large-scale surveillance data handling

---

# Author

Swetha Sivadharshini
Computer Science Engineering Student
