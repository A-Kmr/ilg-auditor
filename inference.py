import os
# Force stable execution flags
os.environ['FLAGS_use_onednn'] = '0'
os.environ['FLAGS_enable_pir_api'] = '0'

import requests 
import cv2
import numpy as np
import csv
from datetime import datetime
from ultralytics import YOLO
from paddleocr import PaddleOCR
from collections import Counter

# Ensure debug directory exists
if not os.path.exists("debug_crops"):
    os.makedirs("debug_crops")

# --- 1. DATA QUALITY GUARDRAIL ---
class TemporalVoter:
    def __init__(self, min_agreement=1): 
        self.history = {}
        self.min_agreement = min_agreement
        self.sent_ids = set() 

    def add_observation(self, track_id, text, confidence):
        if track_id not in self.history:
            self.history[track_id] = []
        if confidence > 0.30: 
            self.history[track_id].append(text)

    def get_voted_result(self, track_id):
        if track_id not in self.history or not self.history[track_id]:
            return "MANUAL_REVIEW"
        votes = Counter(self.history[track_id])
        return votes.most_common(1)[0][0]

# --- 2. INITIALIZATION ---
print("--- Initializing AI Production Models ---")
model = YOLO("yolo11n.pt") 

ocr = PaddleOCR(
    use_angle_cls=True, 
    lang='en', 
    show_log=False,
    det_db_thresh=0.2,        
    det_db_box_thresh=0.4     
)
voter = TemporalVoter(min_agreement=1)

# --- CHANGED: PIVOT TO LOCAL KAGGLE COMPONENT ---
video_filename = "traffic_video_modified.mp4"
cap = cv2.VideoCapture(video_filename)

if not cap.isOpened():
    print(f"❌ CRITICAL ERROR: Could not open {video_filename}. Verify the file is in the project folder!")
    exit()

print(f"--- System Online: Processing Local Stream: {video_filename} ---")

# Open clean CSV file to collect real AI data locally
csv_file = open("real_ai_audit.csv", mode="w", newline="", encoding="utf-8")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["timestamp", "gate_id", "track_id", "vehicle_id", "confidence"]) 

frame_count = 0
ocr_cooldown = {}  

# --- 3. MAIN LOOP ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: 
        print("--- End of Video File Reached ---")
        break

    frame_count += 1

    # YOLO object tracking
    results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
    annotated_frame = results[0].plot()

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().numpy()

        for box, track_id in zip(boxes, track_ids):
            
            # Skip if already compiled and transmitted
            if track_id in voter.sent_ids:
                continue
                
            # Cooldown Throttling to keep video playback frame-rate normal
            if track_id in ocr_cooldown and frame_count < ocr_cooldown[track_id]:
                continue 
                
            x1, y1, x2, y2 = map(int, box)
            crop = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
            
            if crop.size > 0:
                ocr_cooldown[track_id] = frame_count + 15
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                
                # Run OCR scan
                ocr_res = ocr.ocr(gray, cls=True)
                
                if not ocr_res or not ocr_res[0]:
                    print(f"[-] Vehicle Track {track_id}: Scanning image matrix... No text localized yet.")
                    continue
                
                text, conf = ocr_res[0][0][1]
                print(f"[+] Vehicle Track {track_id}: Found Text: '{text}' (Conf: {conf:.2f})")
                
                voter.add_observation(track_id, text, conf)
                final_id = voter.get_voted_result(track_id)
                
                # Local CSV Production Logging
                timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_writer.writerow([timestamp_now, "GATE_NORTH_01", int(track_id), str(final_id), float(conf)])
                csv_file.flush() 
                
                # Container API Linkage
                payload = {
                    "track_id": int(track_id),
                    "reconciled_id": str(final_id),
                    "confidence": float(conf)
                }
                try:
                    r = requests.post("http://127.0.0.1:8000/log-vehicle", json=payload, timeout=0.5)
                    if r.status_code == 200:
                        print(f"   >>> SUCCESS: Sent to Core System Architecture!")
                        voter.sent_ids.add(track_id)
                    else:
                        print(f"   >>> API REJECTED: Status {r.status_code}")
                except Exception as e:
                    print(f"   >>> BRIDGE ERROR: Server unreachable: {e}")

                cv2.putText(annotated_frame, f"ID: {final_id}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Logistics Gateway Auditor", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

# --- CLEANUP LAYER ---
cap.release()
csv_file.close() 
cv2.destroyAllWindows()
print("--- System Offline. Data Safe. ---")