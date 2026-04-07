# ai/face_detector.py
import cv2
import numpy as np
import os

class FaceDetector:
    def __init__(self):
        # Use OpenCV's built-in haarcascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
    def detect_faces(self, image):
        """Detect faces in an image"""
        if image is None:
            return []
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return faces
    
    def extract_face(self, image, face_coords):
        """Extract face region from image"""
        x, y, w, h = face_coords
        face = image[y:y+h, x:x+w]
        return face
    
    def extract_features(self, face_image):
        """Extract simple features from face for comparison"""
        # Resize to standard size
        face_resized = cv2.resize(face_image, (100, 100))
        
        if len(face_resized.shape) == 3:
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_resized
        
        # Extract HOG-like features using gradients
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=1)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=1)
        
        # Calculate magnitude and angle
        mag, ang = cv2.cartToPolar(gx, gy)
        
        # Quantize angle to 9 bins
        bin_count = 9
        angle_bins = np.int32(bin_count * ang / (2*np.pi))
        
        # Create histogram features
        features = []
        for i in range(bin_count):
            mask = angle_bins == i
            features.append(np.sum(mag[mask]))
        
        # Add texture features using LBP-like approach
        lbp = np.zeros_like(gray)
        for i in range(1, gray.shape[0]-1):
            for j in range(1, gray.shape[1]-1):
                center = gray[i, j]
                code = 0
                code |= (gray[i-1, j-1] > center) << 7
                code |= (gray[i-1, j] > center) << 6
                code |= (gray[i-1, j+1] > center) << 5
                code |= (gray[i, j+1] > center) << 4
                code |= (gray[i+1, j+1] > center) << 3
                code |= (gray[i+1, j] > center) << 2
                code |= (gray[i+1, j-1] > center) << 1
                code |= (gray[i, j-1] > center) << 0
                lbp[i, j] = code
        
        # Add LBP histogram
        lbp_hist = cv2.calcHist([lbp.astype(np.uint8)], [0], None, [32], [0, 256])
        lbp_hist = cv2.normalize(lbp_hist, lbp_hist).flatten()
        
        # Combine features
        features = np.array(features + lbp_hist.tolist())
        
        return features / (np.linalg.norm(features) + 1e-6)
