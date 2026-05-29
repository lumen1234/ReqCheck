docker rm -vf reqcheck_container || true
docker run -itd -p 5000:5000 -v "$(pwd)/local_workspaces:/app/local_workspaces" --name reqcheck_container --restart=always rc:v3
