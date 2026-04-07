# FaceTrace – Missing Person Detection System
AI-powered system that identifies missing persons by analyzing CCTV footage using computer vision techniques.


## Overview

FaceTrace is a computer vision based system designed to help identify missing persons by analyzing CCTV video footage. The system allows users to register missing person details and upload CCTV videos. It then detects faces in the video frames and compares them with stored images to find potential matches.

This project aims to assist authorities and organizations in locating missing individuals more efficiently using automated surveillance analysis.

## Features

* User registration and login system
* Missing person registration
* CCTV video upload and processing
* Face detection using OpenCV
* Face comparison and matching
* Admin dashboard for monitoring
* Search history tracking

## Technologies Used

* Python
* Flask
* OpenCV
* NumPy
* SQLite
* HTML
* CSS
* JavaScript

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
└── uploads
```

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

## Future Improvements

* Integration with deep learning face recognition models
* Real-time CCTV camera integration
* Cloud deployment
* Mobile application support

## Author

Swetha Sivadharshini
Computer Science Student
