from datetime import datetime, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='Operator')
    status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, value): self.password_hash = generate_password_hash(value)
    def check_password(self, value): return check_password_hash(self.password_hash, value)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

class Identification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(24), unique=True, nullable=False)
    qr_token = db.Column(db.String(96), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(160)); phone = db.Column(db.String(40)); address = db.Column(db.Text)
    dob = db.Column(db.String(20)); organization = db.Column(db.String(160)); department = db.Column(db.String(120)); designation = db.Column(db.String(120))
    profile_photo = db.Column(db.String(255)); status = db.Column(db.String(20), default='Active'); notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow); updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow); last_scanned_at = db.Column(db.DateTime)
    custom_values = db.relationship('CustomFieldValue', cascade='all, delete-orphan', backref='identification')
    scans = db.relationship('ScanLog', cascade='all, delete-orphan', backref='identification')

class CustomField(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False); label = db.Column(db.String(120), nullable=False)
    field_type = db.Column(db.String(20), default='text'); options = db.Column(db.Text); required = db.Column(db.Boolean, default=False); active = db.Column(db.Boolean, default=True); created_at = db.Column(db.DateTime, default=utcnow)

class CustomFieldValue(db.Model):
    id = db.Column(db.Integer, primary_key=True); identification_id = db.Column(db.Integer, db.ForeignKey('identification.id'), nullable=False); custom_field_id = db.Column(db.Integer, db.ForeignKey('custom_field.id'), nullable=False); value = db.Column(db.Text)
    field = db.relationship('CustomField')

class ScanLog(db.Model):
    id = db.Column(db.Integer, primary_key=True); identification_id = db.Column(db.Integer, db.ForeignKey('identification.id')); qr_token = db.Column(db.String(96), nullable=False); scanned_at = db.Column(db.DateTime, default=utcnow); ip_address = db.Column(db.String(64)); user_agent = db.Column(db.String(255)); status = db.Column(db.String(30), default='Verified')
