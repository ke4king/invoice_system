# 发票管理系统（FastAPI + Vue3）

一个端到端的发票归集与管理平台，后端采用 FastAPI + MySQL + SQLAlchemy + Celery + Redis，前端采用 Vue 3 + Vite + Element Plus。支持邮箱自动抓取发票、OCR（百度）、结构化存储、搜索统计、监控告警、批量打印等。

[English](README.md) | 中文说明

## 功能特性
- 邮箱与手动上传的发票归集
- 百度 OCR 识别，带重试与 QPS 限制
- 用户鉴权（JWT）、角色权限
- 搜索、统计看板、增强日志/监控
- 批量打印与导出（Excel）
- Celery + Redis 异步任务
- Docker Compose 一键启动

## 架构
- 后端：FastAPI、SQLAlchemy、Alembic、Celery、Redis、MySQL
- 前端：Vue 3、Vite、Pinia、Element Plus、ECharts
- 部署：Docker（backend + frontend + MySQL + Redis + Celery worker/beat）

## 快速开始

### 前置条件
- 已安装 Docker 与 Docker Compose v2
- 本地开发（可选）：Node.js 18+、Python 3.11+

### 1）配置环境变量
在项目根目录复制示例环境文件并根据需要修改：

```bash
cp .env.example .env
```

请务必修改 `SECRET_KEY`、数据库账号、OCR 等敏感信息。

### 2）使用 Docker Compose 启动（推荐）

```bash
docker compose up -d --build
```

服务地址：
- 前端：http://localhost
- 后端 API：http://127.0.0.1:8000
- Swagger 文档：http://127.0.0.1:8000/docs

### 3）本地开发辅助脚本（可选）
项目提供 `./start-dev.sh` 用于一键拉起开发环境（容器运行 MySQL/Redis/Celery，本地跑前后端）：

```bash
./start-dev.sh
```

脚本会自动生成 `.env`（若不存在）并启动服务，终端会输出日志与访问地址。

## 配置项
关键环境变量（更多默认值见 `backend/app/core/config.py`）：

- `SECRET_KEY`：JWT/加密密钥
- `DATABASE_URL`：如 `mysql+pymysql://user:pass@localhost:3306/invoice_system`
- `REDIS_URL`：如 `redis://localhost:6379/0`
- `UPLOAD_DIR`：文件存储根目录，默认 `./storage`
- `MAX_FILE_SIZE`：最大上传体积（字节，默认 10MB）
- `BAIDU_OCR_API_KEY`、`BAIDU_OCR_SECRET_KEY`：百度 OCR 凭据
- `OCR_RETRY_TIMES`、`OCR_TIMEOUT`、`OCR_QPS_LIMIT`、`OCR_AMOUNT_IN_CENTS`
- `ADMIN_USERNAME`、`ADMIN_EMAIL`、`ADMIN_PASSWORD`
- `LOG_LEVEL`、`LOG_FILE_MAX_SIZE`、`LOG_FILE_BACKUP_COUNT`
- Cookie/健康检查/限流：`USE_COOKIE_AUTH`、`COOKIE_SECURE`、`HEALTH_REQUIRE_AUTH`、`RATE_LIMIT_ENABLED`

## 目录结构

```
backend/
  app/
    api/api_v1/endpoints/    # 认证、邮件、发票、日志、打印 API
    core/                    # 配置、数据库、依赖、日志、指标
    models/                  # 数据模型
    schemas/                 # Pydantic 模型
    services/                # 业务服务（OCR、邮件、发票等）
    workers/                 # Celery 应用与任务
    main.py                  # FastAPI 入口
  Dockerfile
  requirements.txt
frontend/
  src/                      # Vue 3 应用（Vite + Element Plus）
  Dockerfile
docker-compose.yml          # 生产/预览
docker-compose.dev.yml      # 开发（容器化基础设施 + celery）
start-dev.sh                # 本地开发脚本
```

## API
- 健康检查：`GET /health`、`GET /health/detailed`
- 状态：`GET /api/status`
- OpenAPI：`GET /docs`

## 开发
- 后端开发服务：`uvicorn app.main:app --reload`
- 前端开发服务：在 `frontend/` 目录执行 `npm run dev`
- 后端测试：在 `backend/` 目录执行 `pytest`

## 安全
- 不要提交真实密钥与密码。使用 `.env`（已被 git 忽略），公共示例请改 `.env.example`。
- 管理员密码务必设置为复杂强口令，并定期轮换。

## 贡献
欢迎提交 Issue 与 PR！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 并遵守[社区行为准则](CODE_OF_CONDUCT.md)。

## 许可证
使用 MIT 协议发布，详见 [LICENSE](LICENSE)。

