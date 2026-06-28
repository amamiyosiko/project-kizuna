# Production Docker Deployment

Project Kizuna 从 v0.2.2 开始使用生产构建方式部署。

## 服务
- frontend: Next.js production server, port 3000
- backend: FastAPI / Uvicorn, port 8000
- db: PostgreSQL 16, port 5432
- redis: Redis 7, port 6379

## 正常部署
```bash
cd /www/wwwroot/project-kizuna.mychisyou.com
cp backend/.env /tmp/kizuna-backend.env.bak || true
git reset --hard
git clean -fd
git pull
cp /tmp/kizuna-backend.env.bak backend/.env
docker compose down
docker compose up -d --build
```

## 检查
```bash
docker compose ps
curl http://127.0.0.1:3000
curl http://127.0.0.1:8000/docs
```

## 注意
- 不在服务器直接修改代码。
- backend/.env 只保存在服务器，不提交 GitHub。
- 所有图片和附件继续使用 S3。
