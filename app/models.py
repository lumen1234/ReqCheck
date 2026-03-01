from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Document(db.Model):
    id = db.Column(db.String(32), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='已上传')
    
    requirement_trees = db.relationship('RequirementTree', backref='document', lazy=True)
    validation_results = db.relationship('ValidationResult', backref='document', lazy=True)

class RequirementTree(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.String(32), db.ForeignKey('document.id'), nullable=False)
    tree_json = db.Column(db.JSON, nullable=False)
    parse_time = db.Column(db.DateTime, default=datetime.utcnow)

class ValidationResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.String(32), db.ForeignKey('document.id'), nullable=False)
    result_json = db.Column(db.JSON, nullable=False)
    validate_time = db.Column(db.DateTime, default=datetime.utcnow)
    model_used = db.Column(db.String(100), nullable=True)