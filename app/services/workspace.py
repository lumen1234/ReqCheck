"""工作区路径初始化。"""
import os

WORKSPACE_SUBDIRS = (
    "uploads",
    "parse_results",
    "parse_assets",
    "validate_results",
    "export_results",
)


def init_workspace_dirs(app) -> None:
    base = app.config["LOCAL_WORKSPACES_DIR"]
    os.makedirs(base, exist_ok=True)
    for sub in WORKSPACE_SUBDIRS:
        os.makedirs(os.path.join(base, sub), exist_ok=True)


def parse_results_folder(app) -> str:
    return app.config["PARSE_RESULTS_FOLDER"]


def parse_assets_folder(app) -> str:
    return app.config["PARSE_ASSETS_FOLDER"]


def validate_results_folder(app) -> str:
    return app.config["VALIDATE_RESULTS_FOLDER"]


def export_results_folder(app) -> str:
    return app.config["EXPORT_RESULTS_FOLDER"]
