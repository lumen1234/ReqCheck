from app import app
from app.routes.upload import upload_bp
from app.routes.parse import parse_bp
from app.routes.validate import validate_bp
from app.routes.export import export_bp
from app.routes.history import history_bp

app.register_blueprint(upload_bp)
app.register_blueprint(parse_bp)
app.register_blueprint(validate_bp)
app.register_blueprint(export_bp)
app.register_blueprint(history_bp)
