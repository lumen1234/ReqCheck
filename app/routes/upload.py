from flask import Blueprint, request, jsonify
from app import app
from app.models import db, Document
import os
import uuid

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    file_type = request.form.get('file_type', 'other')
    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # 保存到数据库
    document = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_path=filepath
    )
    db.session.add(document)
    db.session.commit()
    
    return jsonify({
        'doc_id': doc_id,
        'filename': file.filename,
        'file_type': file_type,
        'filepath': filepath
    })

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
