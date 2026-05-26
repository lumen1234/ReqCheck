# ReqCheck Docker 操作指南

本文档整理在 **WSL + Docker** 环境下部署 ReqCheck 的常用命令、实际踩坑与推荐流程，便于学习与复现。

---

## 1. 环境准备

| 组件 | 说明 |
|------|------|
| Windows | 宿主机，代码在 `E:\ReqCheck` |
| WSL | Linux 子系统，终端里路径为 `/mnt/e/ReqCheck` |
| Docker | 在 WSL 内运行，构建并启动容器 |

进入项目目录：

```bash
wsl
cd /mnt/e/ReqCheck
```

查看 Docker 是否可用：

```bash
docker version
docker images
```

---

## 2. 项目相关文件

| 文件 | 作用 |
|------|------|
| [Dockerfile](../Dockerfile) | 多阶段构建：Node 编译前端 → Python 运行后端 |
| [docker-compose.yml](../docker-compose.yml) | 一键 build/run，挂载数据卷 |
| [run.sh](../run.sh) | 简易脚本：删旧容器 + 用 `rc:v3` 镜像启动 |
| [run.py](../run.py) | **容器内**启动命令（`CMD`），不是 bash 脚本 |

### Dockerfile 构建流程简述

```
阶段 1 (node:20)     npm ci → npm run build → frontend/dist
阶段 2 (python:3.10) 换清华 apt 源 → 安装 LibreOffice → pip 装依赖
                     COPY 代码 + 前端 dist → CMD python run.py
```

**为何装 LibreOffice？** Word 文档图片多为 EMF 格式，Linux 下需 LibreOffice 转为 PNG，浏览器才能显示。

---

## 3. 你终端里做过的操作（复盘）

### 3.1 查看已有镜像

```bash
docker images
```

示例输出含义：

| 列 | 含义 |
|----|------|
| REPOSITORY | 镜像名，如 `rc`、`reqcheck` |
| TAG | 版本标签，如 `v3`、`latest` |
| IMAGE ID | 镜像唯一 ID |
| SIZE | 镜像大小 |

### 3.2 构建镜像（你使用的方式）

```bash
cd /mnt/e/ReqCheck
docker build -t rc:v3 .
```

- `-t rc:v3`：打标签为 `rc:v3`（名称:版本）
- `.`：使用当前目录的 `Dockerfile`
- 构建成功末尾：`Successfully tagged rc:v3`

**构建较慢的步骤：** `apt-get install libreoffice-writer-nogui`（体积大）。Dockerfile 已配置清华 apt / pip 源加速。

### 3.3 用脚本启动容器（run.sh）

```bash
bash run.sh
```

`run.sh` 实际执行：

```bash
docker rm -vf reqcheck_container || true
docker run -itd -p 5000:5000 --name reqcheck_container --restart=always rc:v3
```

| 参数 | 含义 |
|------|------|
| `docker rm -vf reqcheck_container` | 删除同名旧容器（若不存在会报错，`\|\| true` 忽略） |
| `docker run -itd` | 后台交互式运行 |
| `-p 5000:5000` | 宿主机 5000 → 容器 5000 |
| `--name reqcheck_container` | 容器名 |
| `--restart=always` | 开机/崩溃后自动重启 |
| `rc:v3` | 使用的镜像 |

访问：`http://localhost:5000` 或 `http://172.30.x.x:5000`（WSL 网关 IP）。

### 3.4 删除镜像

```bash
docker rmi rc:v3
```

注意：若有容器仍在使用该镜像，需先 `docker rm` 停删容器。

### 3.5 误操作：`bash run.py`

```bash
bash run.py   # ❌ 错误
```

`run.py` 是 **Python 程序**，不是 shell 脚本。在容器外应：

```bash
python run.py          # Windows 本地开发
# 或在容器内由 Docker CMD 自动执行
```

---

## 4. 推荐方式：docker compose

比手写 `docker run` 更易维护，与 [docker-compose.yml](../docker-compose.yml) 一致。

```bash
cd /mnt/e/ReqCheck

# 构建并启动（后台）
docker compose up -d --build

# 查看日志
docker compose logs -f

# 停止
docker compose down

# 强制重建（改 Dockerfile 后）
docker compose build --no-cache
docker compose up -d
```

compose 中服务名 `reqcheck`，镜像名 `reqcheck:latest`，容器名 `reqcheck`。

---

## 5. 常用 Docker 命令速查

### 容器

```bash
docker ps              # 运行中的容器
docker ps -a           # 所有容器（含已停止）
docker logs reqcheck   # 查看日志
docker logs -f reqcheck   # 实时跟踪
docker exec -it reqcheck bash   # 进入容器 shell
docker stop reqcheck
docker start reqcheck
docker restart reqcheck
docker rm -f reqcheck  # 强制删除容器
```

### 镜像

```bash
docker images
docker build -t reqcheck:latest .
docker rmi reqcheck:latest
docker history reqcheck:latest   # 查看镜像层
```

### 保存 / 加载镜像（离线拷贝）

```bash
# 导出到 tar（备份或拷到其他机器）
docker save -o /mnt/e/ReqCheck/reqcheck.tar reqcheck:latest

# 压缩（可选）
docker save reqcheck:latest | gzip > reqcheck.tar.gz

# 在其他机器导入
docker load -i reqcheck.tar
```

---

## 6. 数据卷与 Windows 同步

容器内工作目录：`/app/local_workspaces`（上传、解析 JSON、图片等）。

默认 compose 使用 **Docker 命名卷** `reqcheck_local`，与 Windows 上 `E:\ReqCheck\local_workspaces` **不自动同步**。

### 开发时与 Windows 共用同一份数据

编辑 `docker-compose.yml`，注释命名卷，改为绑定挂载：

```yaml
volumes:
  - uniportal_storage:/data/uniportal:ro
  - ./local_workspaces:/app/local_workspaces
```

然后：

```bash
docker compose up -d --force-recreate
```

这样在 Windows 本地解析好的 PNG 图片，容器内也能直接读到。

---

## 7. 端口冲突（重要）

若 **同时** 运行：

- WSL Docker 映射 `5000:5000`
- Windows 上 `python run.py`（也监听 5000）

浏览器访问 `localhost:5000` 可能连到 **旧容器**，出现：表格/图片不显示、JSON 路径为 `/app/app/parse_results/` 等。

**处理：**

```bash
# 只保留一种方式
docker compose down          # 停 Docker
# 或停 Windows 上的 python run.py，只用 Docker
```

验证是否连对服务：

```bash
curl -I http://127.0.0.1:5000/api/parse/<doc_id>/assets/img_001.png
# 应返回 200，Content-Type: image/png
```

---

## 8. 构建 / 运行后验证清单

1. **容器在跑：** `docker ps` 看到 `reqcheck` 或 `reqcheck_container`
2. **首页可开：** 浏览器打开 `http://localhost:5000`
3. **解析 API：** `GET /api/documents` 返回 200
4. **图片 API：** 直接打开 `/api/parse/<doc_id>/assets/img_001.png` 能看到图
5. **强制重解析（更新结构/图片）：**  
   `http://localhost:5000/api/parse/<doc_id>?force=1`

---

## 9. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `apt update` 很慢 | 默认 Debian 国外源 | Dockerfile 已换清华源，需 `--no-cache` 重建 |
| 图片 404 | 旧镜像无 assets 路由 | 重建镜像并重启容器 |
| 图片 304 响应体空 | 正常缓存行为 | 硬刷新；或禁用 DevTools 缓存 |
| 图片不显示、文件是 EMF | Linux 未转 PNG | 确保镜像含 LibreOffice；`?force=1` 重解析 |
| `No such container: reqcheck_container` | 首次运行无旧容器 | 可忽略，或改 `run.sh` 用 `\|\| true` |
| `bash run.py` 报错 | 用 bash 跑 Python | 用 `python run.py` 或 Docker 启动 |
| 表格/树结构不对 | 用了旧缓存 JSON | `?force=1` 重新解析 |

---

## 10. 完整流程示例（从零到可访问）

```bash
# 1. 进入 WSL 项目目录
cd /mnt/e/ReqCheck

# 2. 构建镜像（首次或改 Dockerfile 后）
docker compose build --no-cache

# 3. 启动
docker compose up -d

# 4. 看日志确认无报错
docker compose logs -f

# 5. 浏览器访问
#    http://localhost:5000

# 6. 上传文档后强制解析
#    http://localhost:5000/api/parse/<doc_id>?force=1

# 7. 备份镜像（可选）
docker save -o reqcheck.tar reqcheck:latest
```

---

## 11. run.sh 与 docker compose 的区别

| 方式 | 镜像名 | 容器名 | 数据卷 |
|------|--------|--------|--------|
| `bash run.sh` | `rc:v3` | `reqcheck_container` | 无（数据在容器内，删容器即丢） |
| `docker compose up` | `reqcheck` | `reqcheck` | 挂载 `reqcheck_local` 等 |

**建议：** 日常开发统一用 `docker compose`；`run.sh` 适合快速试跑旧标签 `rc:v3`。

---

## 12. 延伸阅读

- [JSON 生成逻辑说明](./JSON_GENERATION.md)
- [UniPortal 集成](./UNIPORTAL_INTEGRATION.md)
- [Docker 官方文档](https://docs.docker.com/)
