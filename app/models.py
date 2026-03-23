from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ParkingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    entry_time = db.Column(db.DateTime, default=datetime.now)
    entry_image = db.Column(db.String(200))  # Path to image
    exit_time = db.Column(db.DateTime, nullable=True)
    exit_image = db.Column(db.String(200), nullable=True)
    fee = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='parked')  # parked, exited

class Whitelist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    owner_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)

class Garage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="默认车库")
    total_spots = db.Column(db.Integer, default=100)
    hourly_rate = db.Column(db.Float, default=5.0)
    free_minutes = db.Column(db.Integer, default=30)
    
    # New Fields
    daily_max_fee = db.Column(db.Float, default=50.0)
    address = db.Column(db.String(200), default="未设置地址")
    contact_phone = db.Column(db.String(50))
    status = db.Column(db.Integer, default=1) # 1: Open, 0: Closed
    garage_type = db.Column(db.String(50), default="室内") # e.g. "室内", "露天", "立体"

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    moonshot_api_key = db.Column(db.String(200), nullable=True)
    ai_role_prompt = db.Column(db.Text, default="你是一个智能停车助手，负责回答用户关于费率、车位和停车流程的问题。")
    ai_model = db.Column(db.String(50), default="moonshot-v1-8k")

class AlarmLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    event_type = db.Column(db.String(50)) # e.g. "Blacklist", "Forced Open"
    description = db.Column(db.String(200))
    related_plate = db.Column(db.String(20))

class Notice(db.Model):
    """系统公告"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    notice_type = db.Column(db.String(20), default='info')  # info, warning, success, danger
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class OperationLog(db.Model):
    """操作日志"""
    id = db.Column(db.Integer, primary_key=True)
    operator = db.Column(db.String(50), nullable=False)  # 操作人
    operation_type = db.Column(db.String(50), nullable=False)  # 操作类型: edit_record, delete_record等
    target_type = db.Column(db.String(50))  # 目标类型: parking_record, whitelist等
    target_id = db.Column(db.Integer)  # 目标ID
    old_value = db.Column(db.Text)  # 修改前的值（JSON格式）
    new_value = db.Column(db.Text)  # 修改后的值（JSON格式）
    description = db.Column(db.String(200))  # 操作描述
    ip_address = db.Column(db.String(50))  # IP地址
    created_at = db.Column(db.DateTime, default=datetime.now)
