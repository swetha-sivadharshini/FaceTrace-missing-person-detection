import cv2
import numpy as np
import os

class FaceRecognizer:
    def __init__(self, target_size=(100, 100)):
        """
        Initialize face recognizer
        
        Args:
            target_size: Size to resize faces to (width, height)
        """
        self.target_size = target_size
    
    def extract_face_features(self, image, face_box):
        """
        Extract normalized face features from image
        
        Args:
            image: BGR image containing the face
            face_box: Tuple (x, y, w, h) of face bounding box
            
        Returns:
            Normalized grayscale face image (resized, pixel values 0-1)
        """
        x, y, w, h = face_box
        
        # Extract face region
        face = image[y:y+h, x:x+w]
        
        # Convert to grayscale
        if len(face.shape) == 3:
            gray_face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        else:
            gray_face = face
        
        # Resize to target size
        resized_face = cv2.resize(gray_face, self.target_size)
        
        # Normalize to 0-1 range
        normalized_face = resized_face.astype(np.float32) / 255.0
        
        return normalized_face
    
    def compare_faces(self, face1, face2, threshold=0.6):
        """
        Compare two normalized face images
        
        Args:
            face1: First normalized face image
            face2: Second normalized face image
            threshold: Euclidean distance threshold for match
            
        Returns:
            True if faces match (distance < threshold), False otherwise
        """
        # Ensure faces are the same size
        if face1.shape != face2.shape:
            # Resize face2 to match face1 if needed
            face2 = cv2.resize(face2, (face1.shape[1], face1.shape[0]))
        
        # Flatten the images
        flat_face1 = face1.flatten()
        flat_face2 = face2.flatten()
        
        # Calculate Euclidean distance
        distance = np.linalg.norm(flat_face1 - flat_face2)
        
        # Normalize distance by number of pixels
        normalized_distance = distance / len(flat_face1)
        
        return normalized_distance < threshold, normalized_distance
    
    def extract_face_from_image(self, image_path):
        """
        Helper function to extract face features from an image file
        
        Args:
            image_path: Path to image file
            
        Returns:
            Normalized face features or None if no face detected
        """
        from .face_detector import FaceDetector
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Detect faces
        detector = FaceDetector()
        faces = detector.detect_faces(img)
        
        if not faces:
            return None
        
        # Use the first detected face
        return self.extract_face_features(img, faces[0])


# Convenience functions
def extract_face_features(image, face_box):
    """Convenience function to extract face features"""
    recognizer = FaceRecognizer()
    return recognizer.extract_face_features(image, face_box)


def compare_faces(face1, face2, threshold=0.6):
    """Convenience function to compare faces"""
    recognizer = FaceRecognizer()
    return recognizer.compare_faces(face1, face2, threshold)