from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class DocumentBatch(db.Model):
	id = db.Column(db.String(32), primary_key=True)
	name = db.Column(db.String(255), nullable=False)
	upload_time = db.Column(db.DateTime, default=datetime.utcnow)
	status = db.Column(db.String(50), default="已上传")
	documents = db.relationship("Document", backref="batch", lazy=True, order_by="Document.batch_order")

class Document(db.Model):
	id = db.Column(db.String(32), primary_key=True)
	filename = db.Column(db.String(255), nullable=False)
	file_type = db.Column(db.String(100), nullable=False)
	file_path = db.Column(db.String(500), nullable=False)
	upload_time = db.Column(db.DateTime, default=datetime.utcnow)
	status = db.Column(db.String(50), default="已上传")
	batch_id = db.Column(db.String(32), db.ForeignKey("document_batch.id"), nullable=True)
	batch_order = db.Column(db.Integer, nullable=True)
	original_relative_path = db.Column(db.String(500), nullable=True)
	requirement_trees = db.relationship("RequirementTree", backref="document", lazy=True)

class RequirementTree(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	doc_id = db.Column(db.String(32), db.ForeignKey("document.id"), nullable=False)
	tree_json = db.Column(db.JSON, nullable=False)
	parse_time = db.Column(db.DateTime, default=datetime.utcnow)

class ValidationResult(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	doc_id = db.Column(db.String(32), nullable=False)
	result_json = db.Column(db.JSON, nullable=False)
	validate_time = db.Column(db.DateTime, default=datetime.utcnow)
	model_used = db.Column(db.String(100), nullable=True)

class LLMConfig(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	api_key = db.Column(db.String(256), nullable=False)
	base_url = db.Column(db.String(256), nullable=False)
	model = db.Column(db.String(128), nullable=False)
