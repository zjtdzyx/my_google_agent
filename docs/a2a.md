# Agent2Agent (A2A) 项目落地复盘

**日期**: 2025-12-02
**项目**: Google ADK Agent2Agent Communication Implementation

## 1. 项目背景与目标
本项目旨在基于 Google ADK (Agent Development Kit) 的 A2A 协议，构建一个解耦的、可扩展的多智能体协作系统。
核心目标是实现“服务提供者 (Provider)”与“服务消费者 (Consumer)”的分离，模拟真实的微服务架构。

## 2. 架构演进

### 2.1 初始阶段 (Notebook 探索)
- **状态**: 所有代码（Agent 定义、服务启动、客户端调用）混杂在一个 Jupyter Notebook 中。
- **问题**: 
  - 无法模拟真实的进程间通信。
  - 难以进行自动化测试。
  - 代码复用性差，配置分散。

### 2.2 模块化阶段 (MVP 落地)
我们将系统拆分为三个独立文件：
1.  `product_catalog_service.py`: 独立运行的 FastAPI/Uvicorn 服务。
2.  `customer_support_client.py`: 独立的 CLI 客户端。
3.  `integration_tests.py`: 基于 `unittest` 的自动化测试套件。

### 2.3 工程化重构 (Clean Architecture)
为了遵循软件工程最佳实践，我们进行了目录结构重构：

```text
d:\Agents\my_google_agent\
├── config/
│   └── settings.py          # 统一配置中心 (Env, SSL, Constants)
├── src/
│   ├── services/
│   │   └── product_catalog.py  # 服务端 (Provider)
│   └── client/
│   │   └── customer_support.py # 客户端 (Consumer)
├── tests/
│   └── test_integration.py     # 测试套件
└── docs/
    └── project_retrospective.md # 本文档
```

## 3. 遇到的挑战与解决方案

### 3.1 Windows SSL 证书问题
- **现象**: `FileNotFoundError: [Errno 2] No such file or directory` (ssl.py)。
- **原因**: Windows 环境下 Python 无法自动定位系统根证书。
- **解决**: 
  - 引入 `certifi` 库。
  - 在 `config/settings.py` 中强制设置环境变量：
    ```python
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    ```

### 3.2 环境变量管理
- **现象**: 服务端启动报错 `Missing key inputs argument`。
- **原因**: `product_catalog_service.py` 作为独立进程启动时，未加载 `.env` 文件。
- **解决**: 在 `config/settings.py` 中统一调用 `load_dotenv()`，并增加 `get_api_key()` 校验函数。

### 3.3 A2A 协议理解
- **核心**: 理解 `RemoteA2aAgent` 本质上是一个客户端代理 (Proxy)，它通过读取远程的 `agent-card.json` 来动态构建工具接口。

## 4. 关键成果
1.  **解耦**: 服务端和客户端可以部署在不同的机器上，互不影响。
2.  **健壮性**: 增加了重试机制 (Retry Policy)、健康检查 (Health Check) 和统一日志 (Logging)。
3.  **可测试性**: 拥有了完整的集成测试覆盖，支持 Happy Path 和异常流程测试。

## 5. 未来优化方向
- **数据持久化**: 将 Product Catalog 的字典数据替换为 SQLite/PostgreSQL。
- **容器化**: 编写 `Dockerfile` 和 `docker-compose.yml`，实现一键部署。
- **安全性**: 在 A2A 通信中增加 API Key 认证或 OAuth 机制。
