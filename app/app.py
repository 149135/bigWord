import os
import cv2
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from flask import Flask, render_template, Response, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, User, ParkingRecord, Whitelist, Garage, SystemConfig, AlarmLog, Notice, OperationLog
from ultralytics import YOLO
import sys
from openai import OpenAI
import httpx 

# Ensure project root is in path for imports
sys.path.append(os.getcwd())

# --- Helper for Drawing Text (supports Chinese) ---
def cv2_add_chinese_text(img, text, position, text_color=(0, 255, 0), text_size=30):
    try:
        if isinstance(img, np.ndarray):
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            # Try to load a common Chinese font on Windows
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
    
    # Fallback to OpenCV
    cv2.putText(img, text, position, cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
    return img

# Import existing OCR utility
try:
    from utils.plate_ocr_paddle import get_plate_number_paddle
except ImportError as e:
    print(f"Warning: Could not import utils.plate_ocr_paddle: {e}")
    # Fallback to a dummy function that logs the error
    def get_plate_number_paddle(img, coords): 
        print("OCR fallback triggered due to import error")
        return ""

# Configuration
class Config:
    SECRET_KEY = 'dev-secret-key' # Change this in production
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../parking_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'app/static/uploads'

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Global Load Models (Lazy loading recommended, but here for simplicity)
try:
    # Load your YOLO model
    model = YOLO('runs/train/yolov8n/weights/best.pt') 
except:
    print("Warning: Could not load YOLO model at runs/train/yolov8n/weights/best.pt, using yolov8n.pt")
    model = YOLO('yolov8n.pt')

# --- Helper Functions ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def process_frame(frame, is_entry=True):
    """
    Process a single frame: Detect Plate -> OCR -> Logic
    Returns: Annotated Frame, Detection Info (if any)
    """
    results = model(frame, conf=0.4)
    detected_info = None
    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Draw Bounding Box
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Crop Plate for OCR
            plate_img = frame[y1:y2, x1:x2]
            
            # OCR
            # Note: utils expects specific format, but we'll just pass image and coords
            plate_text = get_plate_number_paddle(frame, [x1, y1, x2, y2])
            
            # Draw Text
            cv2.putText(frame, plate_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            detected_info = {
                'plate': plate_text,
                'coords': (x1, y1, x2, y2)
            }
            # Only process one plate per frame for simplicity
            break 
            
    return frame, detected_info

# --- Routes ---

@app.route('/')
@login_required
def index():
    # Dashboard
    settings = Garage.query.first()
    if not settings:
        settings = Garage()
        db.session.add(settings)
        db.session.commit()
        
    parked_count = ParkingRecord.query.filter_by(status='parked').count()
    available = settings.total_spots - parked_count
    
    # Get recent 8 records for dashboard
    recent_records = ParkingRecord.query.order_by(ParkingRecord.entry_time.desc()).limit(8).all()
    
    # Get active notices (最新3条)
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(3).all()
    
    return render_template('index.html', 
                           available_spots=available, 
                           total_spots=settings.total_spots,
                           parked_count=parked_count,
                           recent_records=recent_records,
                           notices=notices)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- AI Assistant API ---
@app.route('/api/kimi', methods=['POST'])
@login_required
def chat():
    """
    AI Chat Assistant Endpoint
    """
    data = request.json
    user_msg = data.get('message')
    
    # Use global system config instead of garage
    config = SystemConfig.query.first()
    garage = Garage.query.first()
    
    if not config or not config.moonshot_api_key:
         return jsonify({'reply': "请先在【AI 助手配置】中配置 Moonshot AI API Key。"})

    try:
        # 创建 httpx 客户端（避免 proxies 参数问题）
        http_client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
        )
        
        # 创建 OpenAI 客户端（兼容 openai>=1.0）
        client = OpenAI(
            api_key=config.moonshot_api_key,
            base_url="https://api.moonshot.cn/v1",
            http_client=http_client,  # 使用预配置的 httpx 客户端
        )
        
        # Build Context with Garage Status
        parked_count = ParkingRecord.query.filter_by(status='parked').count()
        info_context = f"""
        你是一个智能停车助手。当前车库状态：
        总车位: {garage.total_spots}
        已占用: {parked_count}
        费率: {garage.hourly_rate}元/小时
        免费时长: {garage.free_minutes}分钟
        """
        
        messages = [
            {"role": "system", "content": config.ai_role_prompt or "You are a helpful assistant."},
            {"role": "system", "content": info_context},
            {"role": "user", "content": user_msg}
        ]
        
        completion = client.chat.completions.create(
            model=config.ai_model or "moonshot-v1-8k",
            messages=messages,
            temperature=0.3,
        )
        
        reply = completion.choices[0].message.content
        return jsonify({'reply': reply})
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"AI Error: {error_msg}")
        print(f"AI Error Traceback:\n{traceback.format_exc()}")
        
        # 提供更详细的错误信息
        if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return jsonify({'reply': "❌ API Key 无效或已过期，请在【AI 助手配置】中重新配置。"})
        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            return jsonify({'reply': "❌ 网络连接超时，请检查网络连接后重试。"})
        elif "rate" in error_msg.lower() or "quota" in error_msg.lower():
            return jsonify({'reply': "❌ API 调用配额已用尽，请检查您的 Moonshot AI 账户余额。"})
        else:
            return jsonify({'reply': f"❌ AI 服务异常：{error_msg}。请联系管理员或在【AI 助手配置】中检查配置。"})


# --- Stats API for Dashboard ---
@app.route('/api/stats')
@login_required
def get_stats():
    # 1. Weekly Traffic (Last 7 days)
    dates = []
    counts = []
    from datetime import timedelta
    today = datetime.now().date()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        dates.append(d.strftime('%m-%d'))
        c = ParkingRecord.query.filter(db.func.date(ParkingRecord.entry_time) == d).count()
        counts.append(c)
    
    # 2. Additional Stats for Dashboard
    total_revenue = db.session.query(db.func.sum(ParkingRecord.fee)).filter(
        ParkingRecord.status == 'exited'
    ).scalar() or 0
    
    today_entries = ParkingRecord.query.filter(
        db.func.date(ParkingRecord.entry_time) == today
    ).count()
    
    # Simple turnover rate: exited today / (total spots * 24h / avg parking time)
    # For simplicity, just show utilization percentage
    garage = Garage.query.first()
    if garage:
        parked_now = ParkingRecord.query.filter_by(status='parked').count()
        utilization = round((parked_now / garage.total_spots * 100), 1) if garage.total_spots > 0 else 0
    else:
        utilization = 0
    
    # VIP count (whitelist)
    vip_count = Whitelist.query.filter_by(is_active=True).count()
        
    return jsonify({
        'traffic_dates': dates,
        'traffic_counts': counts,
        'total_revenue': round(total_revenue, 2),
        'today_entries': today_entries,
        'utilization': utilization,
        'vip_count': vip_count
    })

@app.route('/api/fee_distribution')
@login_required
def fee_distribution():
    """统计费用区间分布"""
    # 只统计已出场的记录
    exited_records = ParkingRecord.query.filter_by(status='exited').all()
    
    # 初始化计数器
    free = 0      # 0元（免费或VIP）
    low = 0       # 0-20元
    medium = 0    # 20-50元
    high = 0      # >50元
    
    for record in exited_records:
        fee = record.fee or 0
        if fee == 0:
            free += 1
        elif fee <= 20:
            low += 1
        elif fee <= 50:
            medium += 1
        else:
            high += 1
    
    return jsonify({
        'free': free,
        'low': low,
        'medium': medium,
        'high': high
    })

# --- Enhanced History API ---
@app.route('/api/edit_record', methods=['POST'])
@login_required
def edit_record():
    """编辑停车记录并记录操作日志"""
    import json
    
    try:
        record_id = request.form.get('id')
        record = ParkingRecord.query.get(record_id)
        
        if not record:
            return jsonify({'success': False, 'message': '记录不存在'})
        
        # 保存旧值用于日志
        old_value = {
            'plate_number': record.plate_number,
            'entry_time': record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': record.exit_time.strftime('%Y-%m-%d %H:%M:%S') if record.exit_time else None,
            'fee': record.fee,
            'status': record.status
        }
        
        # 更新记录
        record.plate_number = request.form.get('plate_number')
        record.status = request.form.get('status')
        record.fee = float(request.form.get('fee') or 0)
        
        # 处理时间
        entry_time_str = request.form.get('entry_time')
        if entry_time_str:
            record.entry_time = datetime.strptime(entry_time_str, '%Y-%m-%dT%H:%M')
        
        exit_time_str = request.form.get('exit_time')
        if exit_time_str:
            record.exit_time = datetime.strptime(exit_time_str, '%Y-%m-%dT%H:%M')
        else:
            record.exit_time = None
        
        # 新值
        new_value = {
            'plate_number': record.plate_number,
            'entry_time': record.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': record.exit_time.strftime('%Y-%m-%d %H:%M:%S') if record.exit_time else None,
            'fee': record.fee,
            'status': record.status
        }
        
        # 记录操作日志
        log = OperationLog(
            operator=current_user.username,
            operation_type='edit_record',
            target_type='parking_record',
            target_id=record.id,
            old_value=json.dumps(old_value, ensure_ascii=False),
            new_value=json.dumps(new_value, ensure_ascii=False),
            description=f'修改停车记录 #{record.id}',
            ip_address=request.remote_addr
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '修改成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/history_data')
@login_required
def history_data():
    """AJAX History with filtering and pagination"""
    plate = request.args.get('plate', '')
    date = request.args.get('date', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = ParkingRecord.query
    
    if plate:
        query = query.filter(ParkingRecord.plate_number.like(f'%{plate}%'))
    if date:
        query = query.filter(db.func.date(ParkingRecord.entry_time) == date)
    if status:
        query = query.filter(ParkingRecord.status == status)
        
    # Use paginate
    pagination = query.order_by(ParkingRecord.entry_time.desc()).paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items
    
    data = []
    for r in records:
        data.append({
            'id': r.id,
            'plate': r.plate_number,
            'entry_time': r.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': r.exit_time.strftime('%Y-%m-%d %H:%M:%S') if r.exit_time else '-',
            'fee': r.fee,
            'status': r.status,
            'entry_image': r.entry_image,
            'exit_image': r.exit_image
        })
        
    return jsonify({
        'data': data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

# --- Parking Logic API ---

@app.route('/api/process_entry', methods=['POST'])
@login_required
def process_entry():
    """Handle Entry Logic"""
    plate = request.form.get('plate')
    image_file = request.files.get('image') # Optional upload
    
    from app.services import handle_entry
    result = handle_entry(plate, image_file, model, get_plate_number_paddle)
    return jsonify(result)

@app.route('/api/process_exit', methods=['POST'])
@login_required
def process_exit():
    """Handle Exit Logic"""
    plate = request.form.get('plate')
    image_file = request.files.get('image') # Support exit image upload

    from app.services import handle_exit
    result = handle_exit(plate, image_file, model, get_plate_number_paddle)
    return jsonify(result)

# --- Management Routes ---
@app.route('/history')
@login_required
def history():
    return render_template('data/history.html')

@app.route('/analysis')
@login_required
def analysis():
    return render_template('data/analysis.html')

@app.route('/admin/garage', methods=['GET', 'POST'])
@login_required
def garage_settings():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_garage':
            name = request.form.get('name')
            rate = float(request.form.get('hourly_rate'))
            free = int(request.form.get('free_minutes'))
            spots = int(request.form.get('total_spots'))
            # New fields
            daily_max = float(request.form.get('daily_max_fee') or 0)
            addr = request.form.get('address')
            phone = request.form.get('contact_phone')
            g_type = request.form.get('garage_type')
            
            garage = Garage(
                name=name, hourly_rate=rate, free_minutes=free, total_spots=spots,
                daily_max_fee=daily_max, address=addr, contact_phone=phone, garage_type=g_type
            )
            db.session.add(garage)
            db.session.commit()
            flash('新车库添加成功', 'success')
            
        elif action == 'edit_garage':
            garage_id = request.form.get('garage_id')
            garage = Garage.query.get(garage_id)
            if garage:
                garage.name = request.form.get('name')
                garage.hourly_rate = float(request.form.get('hourly_rate'))
                garage.free_minutes = int(request.form.get('free_minutes'))
                garage.total_spots = int(request.form.get('total_spots'))
                # New fields update
                garage.daily_max_fee = float(request.form.get('daily_max_fee') or 0)
                garage.address = request.form.get('address')
                garage.contact_phone = request.form.get('contact_phone')
                garage.garage_type = request.form.get('garage_type')
                
                db.session.commit()
                flash('车库参数已更新', 'success')
                
        elif action == 'delete_garage':
            garage_id = request.form.get('garage_id')
            garage = Garage.query.get(garage_id)
            if garage:
                if Garage.query.count() <= 1:
                     flash('必须保留至少一个车库配置', 'danger')
                else:
                    db.session.delete(garage)
                    db.session.commit()
                    flash('车库已删除', 'success')

    # Get all garages
    garages = Garage.query.all()
    return render_template('admin/garage.html', garages=garages)

@app.route('/admin/ai', methods=['GET', 'POST'])
@login_required
def ai_settings():
    config = SystemConfig.query.first()
    if not config:
        config = SystemConfig()
        db.session.add(config)
        db.session.commit()
        
    if request.method == 'POST':
        config.moonshot_api_key = request.form.get('api_key')
        config.ai_role_prompt = request.form.get('ai_role_prompt')
        config.ai_model = request.form.get('ai_model')
        db.session.commit()
        flash('AI 助手配置已更新', 'success')
        
    return render_template('admin/ai_settings.html', settings=config)

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def user_manage():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_user':
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            
            if User.query.filter_by(username=username).first():
                 flash('用户名已存在', 'danger')
            else:
                is_admin = (role == 'admin')
                u = User(username=username, is_admin=is_admin)
                u.set_password(password)
                db.session.add(u)
                db.session.commit()
                flash('用户创建成功', 'success')
        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user and user.username != 'admin' and user.id != current_user.id:
                db.session.delete(user)
                db.session.commit()
                flash('用户已删除', 'success')
            else:
                flash('无法删除此用户', 'danger')
        elif action == 'reset_password':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user:
                user.set_password('123456') # Default reset password
                db.session.commit()
                flash('密码已重置为 123456', 'success')
            
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/whitelist', methods=['GET', 'POST'])
@login_required
def whitelist_view():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_whitelist':
            plate = request.form.get('plate')
            owner = request.form.get('owner')
            phone = request.form.get('phone')
            if plate:
                wl = Whitelist(plate_number=plate, owner_name=owner, phone=phone)
                db.session.add(wl)
                db.session.commit()
                flash('白名单添加成功', 'success')
        elif action == 'delete_whitelist':
            wl_id = request.form.get('wl_id')
            wl = Whitelist.query.get(wl_id)
            if wl:
                db.session.delete(wl)
                db.session.commit()
                flash('移除成功', 'success')
        elif action == 'edit_whitelist':
            wl_id = request.form.get('wl_id')
            wl = Whitelist.query.get(wl_id)
            if wl:
                wl.plate_number = request.form.get('plate')
                wl.owner_name = request.form.get('owner')
                wl.phone = request.form.get('phone')
                db.session.commit()
                flash('更新成功', 'success')

    whitelist = Whitelist.query.all()
    return render_template('admin/whitelist.html', whitelist=whitelist)

@app.route('/admin/notices', methods=['GET', 'POST'])
@login_required
def notice_manage():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_notice':
            title = request.form.get('title')
            content = request.form.get('content')
            notice_type = request.form.get('notice_type', 'info')
            is_active = request.form.get('is_active') == '1'
            
            if title and content:
                notice = Notice(
                    title=title, 
                    content=content, 
                    notice_type=notice_type,
                    is_active=is_active
                )
                db.session.add(notice)
                db.session.commit()
                flash('公告发布成功', 'success')
        
        elif action == 'edit_notice':
            notice_id = request.form.get('notice_id')
            notice = Notice.query.get(notice_id)
            if notice:
                notice.title = request.form.get('title')
                notice.content = request.form.get('content')
                notice.notice_type = request.form.get('notice_type', 'info')
                notice.is_active = request.form.get('is_active') == '1'
                db.session.commit()
                flash('公告更新成功', 'success')
        
        elif action == 'delete_notice':
            notice_id = request.form.get('notice_id')
            notice = Notice.query.get(notice_id)
            if notice:
                db.session.delete(notice)
                db.session.commit()
                flash('公告删除成功', 'success')
    
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template('admin/notices.html', notices=notices)

# Deprecated old manage route
@app.route('/manage', methods=['GET', 'POST'])
@login_required
def manage():
    return redirect(url_for('garage_settings'))

# --- Video Streaming Generators ---
def generate_frames(camera_id=0):
    """
    Generator for Video Streaming
    camera_id: 0 for webcam, or video file path
    """
    cap = cv2.VideoCapture(camera_id)
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        # Here we could do real-time detection, but for browser performance
        # usually we just stream the video, and the frontend sends 'snapshots' 
        # to the API, OR we do detection here on every Nth frame.
        # Let's do lightweight detection here.
        
        # frame, _ = process_frame(frame) # Uncomment for server-side drawing
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed/<mode>')
@login_required
def video_feed(mode):
    # Entry camera: 0, Exit camera: 1
    cam_id = 0 if mode == 'entry' else 1
    return Response(generate_frames(cam_id), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Initialization ---
def init_db():
    with app.app_context():
        db.create_all()
        # Create Default Admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Default Garage
        if not Garage.query.first():
            db.session.add(Garage(name="默认车库"))
        
        # Default SystemConfig
        if not SystemConfig.query.first():
            db.session.add(SystemConfig())
        
        # Default Notices
        if Notice.query.count() == 0:
            notices_data = [
                {
                    'title': '系统上线通知',
                    'content': '智能停车管理系统已正式上线！支持车牌自动识别、智能计费、数据分析等功能。',
                    'notice_type': 'success',
                    'is_active': True
                },
                {
                    'title': '收费标准说明',
                    'content': '当前停车费率：5元/小时，前30分钟免费。白名单车辆享受免费停车待遇。',
                    'notice_type': 'info',
                    'is_active': True
                },
                {
                    'title': '安全提醒',
                    'content': '请妥善保管您的账号密码，定期修改密码以确保系统安全。如发现异常请及时联系管理员。',
                    'notice_type': 'warning',
                    'is_active': True
                },
                {
                    'title': 'AI助手功能上线',
                    'content': '新增AI智能助手功能，可以实时解答关于停车费率、车位信息等问题。点击右下角聊天图标开始使用。',
                    'notice_type': 'info',
                    'is_active': True
                }
            ]
            
            for notice_data in notices_data:
                notice = Notice(**notice_data)
                db.session.add(notice)
                
        db.session.commit()
        print("Initialized Database with admin/admin123")

if __name__ == '__main__':
    if not os.path.exists('app/static/uploads'):
        os.makedirs('app/static/uploads')
    init_db()
    app.run(debug=True, port=5000)
