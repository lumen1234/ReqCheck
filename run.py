import os

from app import app, FRONTEND_DIST

if __name__ == '__main__':
    if not os.path.isdir(FRONTEND_DIST) or not os.path.exists(os.path.join(FRONTEND_DIST, 'index.html')):
        print('警告: 未找到 frontend/dist/index.html，请先运行 scripts\\build-frontend.bat')
    uni = app.config.get('UNIPORTAL_STORAGE_PATH')
    if uni:
        subdir = app.config.get('UNIPORTAL_EXPORT_SUBDIR', 'document-validator')
        print(f'UniPortal 集成已启用: UNIPORTAL_STORAGE_PATH={uni}')
        print(f'导出 JSON 将同步至共享卷: {{portal_project_id}}/{{item_id}}/{subdir}/export_{{item_id}}.json')
    else:
        print('UniPortal 集成未启用（独立模式，仅本地上传；导出仅写 local_workspaces/export_results/）')
    app.run(debug=True, host='0.0.0.0', port=5000)
