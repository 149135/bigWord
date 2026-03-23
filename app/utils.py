import cv2
import numpy as np
from app.app import app, model, get_plate_number_paddle

def detect_plate_from_image(image_path):
    """
    Helper to detect plate from a saved image file
    """
    frame = cv2.imread(image_path)
    if frame is None:
        return None
        
    # Run YOLO
    results = model(frame, conf=0.4)
    
    plate_text = None
    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # OCR
            plate_text = get_plate_number_paddle(frame, [x1, y1, x2, y2])
            if plate_text and "未识别" not in plate_text:
                return plate_text
                
    return plate_text











