import os
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, url_for
from app.models import db, ParkingRecord, Whitelist, Garage
from sqlalchemy.exc import SQLAlchemyError

def cv2_add_chinese_text(img, text, position, text_color=(0, 255, 0), text_size=30):
    try:
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            try:
                font = ImageFont.truetype("simhei.ttf", text_size, encoding="utf-8")
            except OSError:
                try:
                    font = ImageFont.truetype("msyh.ttc", text_size, encoding="utf-8")
                except OSError:
                    font = ImageFont.load_default()
            
            draw.text(position, text, font=font, fill=text_color)
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Drawing text failed: {e}")
    
    cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
    return img

def handle_entry(plate, image_file, model, get_plate_number_paddle):
    """
    Handle vehicle entry logic with transaction safety.
    """
    filename = None
    save_path = None
    detected_image_url = None
    
    try:
        # 1. Handle Image Upload & OCR if needed
        if image_file:
            filename = secure_filename(f"entry_{int(time.time())}_{image_file.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
            
            # Always try to detect for drawing bounding box, even if manual plate provided?
            # User said: "In recognition result show yolov recognized box picture"
            # So we should run detection to get the box if image is provided.
            
            img = cv2.imread(save_path)
            
            if img is not None:
                # Run YOLO detection
                results = model(img, conf=0.4)
                
                detected_plate_in_image = None
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Try OCR multiple times for better stability
                        detected = None
                        for attempt in range(3):  # Try up to 3 times
                            detected = get_plate_number_paddle(img, [x1, y1, x2, y2])
                            if detected and "未识别" not in detected and len(detected) > 0:
                                print(f"✅ OCR成功 (尝试 {attempt + 1}/3): {detected}")
                                break
                            elif attempt < 2:
                                print(f"⚠️ OCR重试 {attempt + 1}/3...")
                                time.sleep(0.3)  # Longer delay before retry (300ms)
                        
                        if detected and "未识别" not in detected and len(detected) > 0:
                            detected_plate_in_image = detected
                            
                            # Draw box and text
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            img = cv2_add_chinese_text(img, detected, (x1, y1 - 40), text_size=40)
                            
                            # Save annotated image
                            detected_filename = f"detected_{filename}"
                            detected_path = os.path.join(current_app.config['UPLOAD_FOLDER'], detected_filename)
                            cv2.imwrite(detected_path, img)
                            detected_image_url = url_for('static', filename=f'uploads/{detected_filename}')
                            
                            break 
                    if detected_plate_in_image: break
                
                # If no manual plate, use detected
                if not plate and detected_plate_in_image:
                    plate = detected_plate_in_image
        
        if not plate:
            if save_path and os.path.exists(save_path):
                # We might want to keep it for debugging, but sticking to cleanup
                pass 
            return {'success': False, 'message': 'No plate detected'}

        # 2. Database Transaction
        
        # Check Whitelist
        whitelist = Whitelist.query.filter_by(plate_number=plate).first()
        is_vip = whitelist is not None

        # Check if already parked
        existing = ParkingRecord.query.filter_by(plate_number=plate, status='parked').first()
        if existing:
            if save_path and os.path.exists(save_path):
                os.remove(save_path) # Cleanup duplicate upload
            return {
                'success': False, 
                'message': f'Vehicle {plate} already in garage', 
                'plate': plate,
                'image_url': detected_image_url
            }

        # Create Record
        record = ParkingRecord(plate_number=plate, entry_image=filename)
        db.session.add(record)
        db.session.commit()
        
        return {
            'success': True, 
            'message': f'Welcome {plate}', 
            'is_vip': is_vip,
            'plate': plate,
            'image_url': detected_image_url
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
        return {'success': False, 'message': f'Database error: {str(e)}'}
    except Exception as e:
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
        return {'success': False, 'message': f'System error: {str(e)}'}

def handle_exit(plate, image_file, model, get_plate_number_paddle):
    """
    Handle vehicle exit logic with transaction safety.
    """
    filename = None
    save_path = None
    processed_image_url = None
    
    try:
        # 1. Handle Image Upload & OCR
        if image_file:
            # Generate unique filename
            filename = secure_filename(f"exit_{int(time.time())}_{image_file.filename}")
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
            
            # If no manual plate, or we want to show detection visualization
            img = cv2.imread(save_path)
            if img is not None:
                results = model(img, conf=0.4)
                detected_plate_in_image = None
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Draw bounding box
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2) # Red for exit
                        
                        # Try OCR multiple times for better stability
                        detected = None
                        for attempt in range(3):  # Try up to 3 times
                            detected = get_plate_number_paddle(img, [x1, y1, x2, y2])
                            if detected and "未识别" not in detected and len(detected) > 0:
                                print(f"✅ 出场OCR成功 (尝试 {attempt + 1}/3): {detected}")
                                break
                            elif attempt < 2:
                                print(f"⚠️ 出场OCR重试 {attempt + 1}/3...")
                                time.sleep(0.3)  # Longer delay before retry (300ms)
                        
                        if detected and "未识别" not in detected and len(detected) > 0:
                            detected_plate_in_image = detected
                            # Draw text
                            img = cv2_add_chinese_text(img, detected, (x1, y1 - 40), (0, 0, 255), 40)
                            
                            # Save annotated image
                            annotated_filename = f"annotated_{filename}"
                            annotated_path = os.path.join(current_app.config['UPLOAD_FOLDER'], annotated_filename)
                            cv2.imwrite(annotated_path, img)
                            processed_image_url = url_for('static', filename=f'uploads/{annotated_filename}')
                            
                            break
                    if detected_plate_in_image: break
                
                # If no manual plate provided, use detected
                if not plate and detected_plate_in_image:
                    plate = detected_plate_in_image
        
        if not plate:
            if save_path and os.path.exists(save_path):
                # Cleanup original upload if failed, but maybe keep for debug?
                # os.remove(save_path) 
                pass
            return {'success': False, 'message': '无法识别车牌，请手动输入'}

        # 2. Database Transaction
        record = ParkingRecord.query.filter_by(plate_number=plate, status='parked').first()
        
        if not record:
            if save_path and os.path.exists(save_path):
                os.remove(save_path)
            return {
                'success': False, 
                'message': f'未找到车牌 {plate} 的入场记录',
                'plate': plate,
                'image_url': processed_image_url
            }
            
        # Calculate Fee
        settings = Garage.query.first() or Garage()
        now = datetime.now()
        duration = now - record.entry_time
        hours = duration.total_seconds() / 3600
        
        fee = 0
        whitelist = Whitelist.query.filter_by(plate_number=plate).first()
        
        if not whitelist:
            if duration.total_seconds() / 60 > settings.free_minutes:
                fee = round(hours * settings.hourly_rate, 2)
                if hasattr(settings, 'daily_max_fee') and settings.daily_max_fee > 0:
                        if fee > settings.daily_max_fee:
                            fee = settings.daily_max_fee

        # Update Record
        record.exit_time = now
        record.fee = fee
        record.status = 'exited'
        if filename:
            record.exit_image = filename # Save original filename
            
        db.session.commit()
        
        return {
            'success': True,
            'message': f'一路顺风 {plate}',
            'fee': fee,
            'duration': f"{hours:.1f} hours",
            'plate': plate,
            'image_url': processed_image_url
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
        return {'success': False, 'message': f'Database error: {str(e)}'}
    except Exception as e:
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
        return {'success': False, 'message': f'System error: {str(e)}'}
