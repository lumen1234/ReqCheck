import os

from app import app, FRONTEND_DIST

if __name__ == '__main__':
    if not os.path.isdir(FRONTEND_DIST) or not os.path.exists(os.path.join(FRONTEND_DIST, 'index.html')):
        print('警告: 未找到 frontend/dist/index.html，请先运行 scripts\\build-frontend.bat')
    uni = app.config.get('UNIPORTAL_STORAGE_PATH')
    if uni:
        print(f'UniPortal 集成已启用: UNIPORTAL_STORAGE_PATH={uni}')
    else:
        print('UniPortal 集成未启用（独立模式，仅本地上传）')
    app.run(debug=True, host='0.0.0.0', port=5000)
