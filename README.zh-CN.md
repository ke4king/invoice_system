# 发票管理系统（FastAPI + Vue3）

一个企业级的智能发票管理平台，采用现代技术栈构建。具备智能邮件采集、高精度OCR处理、实时监控和灵活打印功能，专为需要自动化发票处理的企业打造。

[English](README.md) | 中文说明

## 📸 界面截图

### 仪表板概览
![仪表板](image/dashboard.png)
*实时仪表板显示发票统计、处理指标和系统健康状态*

### 发票管理界面
![发票管理](image/screenshot-1.png)
*发票列表支持高级筛选、搜索和状态管理*

### 邮箱配置
![邮箱设置](image/screenshot-2.png)
*邮箱账户配置，用于自动化发票收集*

### 打印布局选项
![打印设置](image/screenshot-3.png)
*灵活的打印选项，支持每页1/2/4张发票的布局*

### 系统监控
![监控仪表板](image/screenshot-4.png)
*全面的系统监控，包括性能指标和日志*

## ✨ 核心功能

### 📧 智能邮件集成
- **自动化邮件采集**：支持IMAP/POP3协议自动获取发票邮件
- **邮件配置管理**：便捷的多邮箱账户设置和管理
- **异步邮件处理**：基于Celery的高吞吐量邮件处理队列
- **邮件状态追踪**：实时监控邮件处理状态和进度

### 🤖 高级OCR处理
- **百度OCR集成**：高精度中文发票光学字符识别
- **智能重试机制**：指数退避重试策略处理失败请求
- **QPS限流控制**：可配置的速率限制，避免API限制
- **OCR缓存系统**：智能缓存减少重复API调用，提升性能
- **成本优化**：高效的token使用和智能处理策略

### 🔐 安全认证系统
- **JWT身份认证**：安全令牌认证，支持配置过期时间
- **基于角色的权限控制**：细粒度权限系统（管理员、普通用户、只读用户）
- **密码安全**：强密码要求，bcrypt哈希加密
- **会话管理**：安全会话处理，可配置超时时间
- **API速率限制**：内置速率限制防止滥用

### 📊 数据看板与分析
- **实时统计数据**：动态仪表板展示关键指标和KPI
- **交互式图表**：使用ECharts的丰富数据可视化
- **发票分析**：全面的发票处理统计、成功率和趋势分析
- **性能监控**：系统健康指标和性能监控
- **自定义时间范围**：灵活的时间段筛选功能

### 🔍 高级搜索与筛选
- **全文搜索**：跨发票内容、元数据和附件的多字段搜索
- **日期范围筛选**：按上传日期、处理日期或发票日期筛选
- **状态筛选**：按处理状态筛选（待处理、处理中、已完成、失败）
- **邮件来源筛选**：按来源邮箱账户筛选发票
- **分页支持**：大数据集的高效分页处理

### 🖨️ 灵活打印与导出
- **多种布局选项**：
  - 每页1张发票（标准布局）
  - 每页2张发票（紧凑布局）
  - 每页4张发票（超紧凑布局）
- **批量打印**：单次操作打印多张发票
- **Excel导出**：支持自定义模板的Excel数据导出
- **打印预览**：所见即所得的打印预览功能
- **自定义模板**：支持自定义打印模板和布局

### 📈 增强监控与日志
- **实时系统监控**：系统健康和性能的实时指标
- **结构化日志**：可配置级别的结构化日志记录
- **错误追踪**：详细的错误报告和堆栈跟踪
- **性能指标**：响应时间、吞吐量和资源利用率
- **审计追踪**：完整的审计日志用于合规和调试

### ⚡ 异步处理系统
- **Celery集成**：基于Redis消息代理的分布式任务处理
- **任务调度**：使用Celery Beat的定期任务
- **后台作业**：OCR、邮件获取和报告生成的非阻塞处理
- **任务监控**：实时任务状态和进度追踪
- **重试机制**：失败任务的可配置重试策略

### 🐳 运维与部署
- **Docker Compose**：一键启动所有服务
- **多环境支持**：开发、测试、生产环境的独立配置
- **健康检查**：所有服务的自动化健康监控
- **弹性扩展**：支持水平扩展的容器化架构
- **数据库迁移**：使用Alembic的平滑数据库模式更新

## 🏗️ 系统架构

### 后端架构
- **FastAPI**：高性能异步Web框架，用于构建API
- **SQLAlchemy + Alembic**：ORM和数据库迁移工具，用于数据持久化
- **MySQL**：关系型数据库，存储结构化的发票和用户数据
- **Redis**：高性能缓存和Celery消息代理
- **Celery + Celery Beat**：分布式任务队列，用于异步处理
- **Pydantic**：数据验证和序列化
- **JWT**：支持配置过期时间的JWT安全认证

### 前端架构
- **Vue 3**：使用Composition API的渐进式JavaScript框架
- **Vite**：下一代前端工具链，实现快速开发
- **Pinia**：直观的状态管理库
- **Element Plus**：企业级Vue组件库
- **ECharts**：强大的图表和可视化库
- **Vue Router**：官方路由器，支持高级路由功能
- **Axios**：基于Promise的HTTP客户端，用于API通信

### 基础设施与运维
- **Docker + Docker Compose**：容器化部署和编排
- **Nginx**：高性能Web服务器和反向代理
- **Supervisor**：生产环境进程管理
- **GitHub Actions**：自动化测试和部署的CI/CD流水线
- **预构建镜像**：优化后的容器镜像托管在GHCR

### 数据流架构
```
邮件来源 → IMAP/POP3 → 邮件处理 → 发票提取 → OCR处理 → 数据存储
                                                              ↓
用户界面 ← API层 ← 业务逻辑 ← 数据库/Redis ← 后台任务
                                                              ↓
报告分析 ← 监控 ← 日志 ← 错误追踪
```

### 服务组件
- **API网关**：提供RESTful API的FastAPI应用
- **认证服务**：基于JWT的用户认证和授权
- **邮件服务**：自动化邮件采集和处理
- **OCR服务**：集成百度OCR的重试逻辑
- **发票服务**：发票数据处理和管理
- **打印服务**：支持多种布局的灵活打印
- **监控服务**：系统健康和性能监控
- **日志服务**：支持轮转和备份的结构化日志

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

可以选择本地构建镜像，或直接使用 GitHub 容器镜像（GHCR）上的预构建镜像。

使用预构建镜像（推荐在 CI/CD 与服务器环境）：

```bash
export FRONTEND_IMAGE=ghcr.io/ke4king/invoice_system-frontend:latest
export BACKEND_IMAGE=ghcr.io/ke4king/invoice_system-backend:latest

docker compose pull
docker compose up -d
```

如果希望本地构建镜像运行：

```bash
unset FRONTEND_IMAGE BACKEND_IMAGE
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

## 🔌 API文档

### 核心接口

#### 系统健康与状态
- `GET /health` - 基础健康检查
- `GET /health/detailed` - 包含指标的综合系统健康检查
- `GET /api/status` - 应用状态和版本信息
- `GET /docs` - 交互式API文档（Swagger UI）
- `GET /redoc` - 替代API文档（ReDoc）
- `GET /openapi.json` - OpenAPI规范

#### 认证管理
- `POST /api/v1/auth/login` - 用户登录获取JWT令牌
- `POST /api/v1/auth/logout` - 用户登出
- `POST /api/v1/auth/refresh` - 刷新JWT令牌
- `GET /api/v1/auth/me` - 获取当前用户信息

#### 发票管理
- `GET /api/v1/invoices/` - 列出发票（支持筛选和分页）
- `POST /api/v1/invoices/` - 上传新发票
- `GET /api/v1/invoices/{id}` - 获取发票详情
- `PUT /api/v1/invoices/{id}` - 更新发票信息
- `DELETE /api/v1/invoices/{id}` - 删除发票
- `POST /api/v1/invoices/{id}/reprocess` - 重新OCR处理发票

#### 邮件管理
- `GET /api/v1/emails/` - 列出邮件配置
- `POST /api/v1/emails/` - 添加新邮件配置
- `PUT /api/v1/emails/{id}` - 更新邮件配置
- `DELETE /api/v1/emails/{id}` - 删除邮件配置
- `POST /api/v1/emails/{id}/test` - 测试邮件连接

#### 批量操作
- `POST /api/v1/print/batch` - 批量打印发票（支持布局选项）
- `POST /api/v1/export/excel` - 导出发票到Excel格式
- `POST /api/v1/invoices/batch-delete` - 批量删除发票

#### 监控与分析
- `GET /api/v1/monitoring/dashboard` - 仪表板统计数据和指标
- `GET /api/v1/logs/` - 系统日志（支持筛选）
- `GET /api/v1/monitoring/performance` - 性能指标
- `GET /api/v1/monitoring/tasks` - Celery任务状态

#### 系统配置
- `GET /api/v1/configs/` - 列出系统配置
- `PUT /api/v1/configs/{key}` - 更新配置值

### API特性
- **JWT认证**：在Authorization头中使用Bearer令牌
- **基于角色的访问**：管理员/用户角色的不同权限
- **速率限制**：每个端点的可配置速率限制
- **请求验证**：使用Pydantic模型进行输入验证
- **错误处理**：结构化的错误响应和错误码
- **分页**：大数据集的光标分页
- **筛选**：所有列表端点的先进筛选选项
- **CORS支持**：前端的跨域请求支持

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

