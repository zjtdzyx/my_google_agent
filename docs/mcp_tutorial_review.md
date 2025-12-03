# MCP & Agent Workflow 实践复盘 (Day 2)

**日期**: 2025-12-03  
**环境**: Windows, Python 3.x, Google ADK  
**主题**: Model Context Protocol (MCP) 集成与长运行操作 (Human-in-the-Loop)

---

## 1. 概览 (Overview)

本次实践旨在通过 Google ADK (Agent Development Kit) 掌握两个核心的高级 Agent 模式：
1.  **MCP 集成**: 让 Agent 连接外部工具生态（以 `@modelcontextprotocol/server-everything` 为例）。
2.  **长运行操作 (LRO)**: 实现“暂停-等待审批-恢复”的人机协同工作流。

---

## 2. 阶段一：MCP 集成踩坑记录 (Troubleshooting)

在 Windows 环境下通过 Python `subprocess` 驱动 Node.js 编写的 MCP Server 遇到了极大的挑战。

### 🛑 问题 1: 依赖环境缺失
*   **现象**: `ModuleNotFoundError: No module named 'IPython'`
*   **原因**: 教程代码源自 Jupyter Notebook，包含 `IPython.display` 用于展示图片，但我们在纯终端环境下运行。
*   **解决**: 移除 IPython 依赖，改为保存图片到本地文件。

### 🛑 问题 2: `npx` 路径与执行问题
*   **现象**: `shutil.which("npx")` 找不到命令，或者 `subprocess` 调用 `npx` 没有任何反应。
*   **原因**: Windows 下 `npx` 实际上是 `npx.cmd` 批处理文件。Python 在不使用 `shell=True` 时无法直接执行它，且 `npx` 可能会尝试联网下载包，导致超时。
*   **尝试**: 
    *   使用 `shutil.which("npx")` 获取绝对路径。
    *   添加 `--no-install` 参数强制使用本地缓存。
    *   设置 `shell=True` (不推荐，破坏管道)。

### 🛑 问题 3: 核心问题 - "失明"的 Agent (The Silent Failure)
*   **现象**: 
    *   日志显示连接成功 (`✅ MCP Toolset initialized`)。
    *   但 Agent 坚称自己没有工具能力 (`I do not have the functionality...`)。
    *   开启 DEBUG 日志后发现，要么没有 JSON-RPC 交互，要么工具列表为空。
*   **根本原因 (Root Cause)**: 
    *   Windows 的 `npx.cmd` 包装器干扰了标准输入输出 (stdio) 管道。Python 的 `subprocess` 可能连接到了 `cmd.exe` 而不是背后的 `node.exe` 进程，导致 MCP 协议握手失败。
*   **✅ 终极解决方案 (The Nuclear Option)**:
    *   **绕过 npx**: 放弃使用 `npx` 启动 Server。
    *   **物理定位**: 使用 `pnpm list -g ...` 找到包的真实物理路径。
    *   **直接执行**: 修改代码，直接用 `node` 执行入口文件。
    ```python
    # 关键代码变更
    server_path = r"C:\Users\...\node_modules\@modelcontextprotocol\server-everything\dist\index.js"
    mcp_image_server = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="node",  # 直接调用 Runtime
                args=[server_path], # 直接指向入口文件
            ),
            timeout=60,
        )
    )
    ```

### 🛑 问题 4: 工具 Schema 缺失
*   **现象**: 连接终于成功，日志显示加载了 `getTinyImage`，但 Schema 为空 `{}`。Agent 依然拒绝调用。
*   **原因**: LLM 依赖工具描述 (Description) 来决策。空描述导致模型困惑。
*   **解决**: 在 System Instruction 中显式“教” Agent：
    > "You have access to a tool named 'getTinyImage'... You MUST use it."

---

## 3. 阶段二：长运行操作 (LRO) 与人机回环

相比 MCP 的环境坑，这一阶段非常顺利，验证了 ADK 强大的状态管理能力。

### 核心机制
*   **ToolContext**: 工具内部通过 `tool_context.request_confirmation()` 发起暂停请求。
*   **App & Resumability**: 使用 `App(..., resumability_config=ResumabilityConfig(is_resumable=True))` 包装 Agent，确保暂停时状态被保存。
*   **Invocation ID**: 恢复执行的唯一凭证。

### 工作流逻辑
1.  **暂停**: 工具检测到大额订单 -> 请求确认 -> 返回 Pending 状态。
2.  **捕获**: 外部循环捕获 `adk_request_confirmation` 事件。
3.  **决策**: 模拟人工输入 (Approve/Reject)。
4.  **恢复**: 调用 `runner.run_async(..., invocation_id=...)` 传入决策结果。
5.  **继续**: 工具内部 `if tool_context.tool_confirmation` 分支被触发，完成剩余逻辑。

---

## 4. 总结与最佳实践

1.  **Windows 开发 MCP**: 尽量避免通过 `npx`/`npm run` 等中间脚本启动 Server。直接调用 `node` (或 `python`) 执行目标脚本是最稳健的方式。
2.  **调试技巧**: 当 Agent 行为异常时，第一时间开启 `logging.DEBUG` 查看底层的 JSON-RPC 交互。
3.  **Prompt Engineering**: 如果工具定义不完美（缺少描述），可以通过 System Prompt 强行补救。
4.  **状态管理**: ADK 的 `App` 模式完美解决了 LLM 无状态与业务流程有状态之间的矛盾，是构建复杂 Agent 的基石。
