docker rm -vf reqcheck_container || true
docker run -itd -p 5000:5000 --name reqcheck_container --restart=always rc:v3