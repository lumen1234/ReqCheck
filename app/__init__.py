import os

from flask import Flask, send_from_directory
from app.models import db

FRONTEND_DIST = os.path.join(
	os.path.dirname(os.path.dirname(__file__)),
	"frontend",
	"dist",
)

app = Flask(
	__name__,
	static_folder=FRONTEND_DIST,
	static_url_path="",
)
app.config.from_object("config")

from app.services.workspace import init_workspace_dirs

init_workspace_dirs(app)
db.init_app(app)

def _ensure_batch_columns():
	uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
	if not uri.startswith("sqlite"):
		return
	from sqlalchemy import inspect, text
	inspector = inspect(db.engine)
	if "document" not in inspector.get_table_names():
		return
	columns = {column["name"] for column in inspector.get_columns("document")}
	migrations = {
		"batch_id": "ALTER TABLE document ADD COLUMN batch_id VARCHAR(32)",
		"batch_order": "ALTER TABLE document ADD COLUMN batch_order INTEGER",
		"original_relative_path": "ALTER TABLE document ADD COLUMN original_relative_path VARCHAR(500)",
	}
	with db.engine.begin() as conn:
		for column, statement in migrations.items():
			if column not in columns:
				conn.execute(text(statement))

with app.app_context():
	print(app.config["SQLALCHEMY_DATABASE_URI"])
	db.create_all()
	_ensure_batch_columns()

from app.routes import upload, parse, validate, export

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_vue(path):
	dist_dir = app.static_folder
	if path and "?" in path:
		path = path.split("?",1)[0]
	requested_path = os.path.join(dist_dir, path)
	if path and os.path.exists(requested_path):
		return send_from_directory(dist_dir, path)
	return send_from_directory(dist_dir, "index.html")
