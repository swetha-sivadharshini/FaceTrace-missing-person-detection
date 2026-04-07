# ai/video_processor.py
import cv2
import os
import csv
import time
from multiprocessing import Pool, cpu_count
from .face_detector import FaceDetector
from .face_recognition import FaceRecognizer

class VideoProcessor:
    def __init__(self):
        self.frame_interval = 10  # process every 10th frame
        self.save_matches_dir = 'matches'
        os.makedirs(self.save_matches_dir, exist_ok=True)

    def load_location_map(self, csv_path='data/cctv_locations.csv'):
        """Load CCTV location mapping from CSV"""
        location_map = {}
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location_map[row['video_name']] = row.get('location', 'Unknown Location')
        except Exception as e:
            print(f"[Error] Loading location map: {e}")
        return location_map

    def extract_frames(self, video_path, interval=None):
        """Extract frames from video at specified interval"""
        if interval is None:
            interval = self.frame_interval

        frames = []
        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % interval == 0:
                frames.append((frame_count, frame))
            frame_count += 1

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        cap.release()
        return frames, fps

    def process_single_video(self, args):
        """Process a single video file with faster partial results"""
        video_path, target_face, complaint_id = args

        detector = FaceDetector()
        recognizer = FaceRecognizer()

        video_name = os.path.basename(video_path)
        print(f"[INFO] Processing video: {video_name}")

        location_map = self.load_location_map()
        location = location_map.get(video_name, 'Unknown Location')

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = 0
        matches = []
        matched_frames = []

        # Extract target face features once
        target_features = recognizer.extract_face_features(
            target_face,
            (0, 0, target_face.shape[1], target_face.shape[0])
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % self.frame_interval == 0:
                faces = detector.detect_faces(frame)
                for (x, y, w, h) in faces:
                    face_crop = frame[y:y+h, x:x+w]
                    face_features = recognizer.extract_face_features(face_crop, (0, 0, w, h))
                    is_match, confidence = recognizer.compare_faces(target_features, face_features, threshold=0.65)

                    print(f"Frame {frame_count}: Confidence={confidence:.4f}, Match={is_match}")

                    if is_match:
                        print(f"[MATCH] {video_name}, frame {frame_count}, confidence {confidence:.2f}")

                        match_filename = f"match_{complaint_id}_{video_name}_{frame_count}.jpg"
                        match_path = os.path.join(self.save_matches_dir, match_filename)
                        cv2.imwrite(match_path, face_crop)

                        annotated_frame = frame.copy()
                        cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.putText(annotated_frame, f"Match: {confidence:.2f}", (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        annotated_filename = f"annotated_{match_filename}"
                        annotated_path = os.path.join(self.save_matches_dir, annotated_filename)
                        cv2.imwrite(annotated_path, annotated_frame)

                        matches.append({
                            'location': location,
                            'video_name': video_name,
                            'frame_image': match_filename,
                            'annotated_image': annotated_filename,
                            'confidence': confidence,
                            'frame_number': frame_count,
                            'timestamp': frame_count / fps
                        })

                        matched_frames.append(frame)

            frame_count += 1

            # Optional: print progress every 100 frames
            if frame_count % 100 == 0:
                print(f"[INFO] Processed {frame_count} frames in {video_name}")

        cap.release()

        # Save matched video if any matches found
        if matched_frames:
            h, w, _ = matched_frames[0].shape
            out_video_path = os.path.join(self.save_matches_dir, f"matched_{complaint_id}_{video_name}.mp4")
            out = cv2.VideoWriter(out_video_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
            for f in matched_frames:
                out.write(f)
            out.release()
            print(f"[INFO] Matched video saved at {out_video_path}")

        return matches

    def search_face_in_videos(self, video_list, target_face, complaint_id, use_multiprocessing=True):
        """Search for face across multiple videos"""
        args_list = [(video_path, target_face, complaint_id) for video_path in video_list]
        results = []

        if use_multiprocessing:
            num_processes = min(cpu_count(), 4)
            with Pool(num_processes) as pool:
                for match_list in pool.map(self.process_single_video, args_list):
                    results.extend(match_list)
        else:
            for args in args_list:
                results.extend(self.process_single_video(args))

        print(f"[INFO] Total matches found: {len(results)}")
        return results

# Example usage
if __name__ == "__main__":
    processor = VideoProcessor()
    # video_list = ['data/cctv1.mp4', 'data/cctv2.mp4']
    # target_face = cv2.imread('data/missing_person.jpg')
    # complaint_id = '1234'
    # matches = processor.search_face_in_videos(video_list, target_face, complaint_id, use_multiprocessing=False)