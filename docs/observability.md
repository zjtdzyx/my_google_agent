# Agent Observability 落地复盘文档

**日期**: 2025-12-03
**项目**: my_google_agent
**模块**: Agent Observability (Day 4 Tutorial)

## 1. 项目概述

本项目旨在为 `my_google_agent` 集成完整的可观测性（Observability）体系。我们从基础的日志配置出发，通过交互式调试修复 Bug，最终实现了生产级的监控插件。

## 2. 实施模块 (Modules Implemented)

### 模块 A: 基础环境与日志配置 (Foundation)
- **目标**: 建立统一的日志标准。
- **产出**: 重构 `config/settings.py`。
- **亮点**:
    - 实现了 Console (开发) + File (持久化) 双路输出。
    - 支持通过环境变量 `LOG_LEVEL` 动态调整日志级别。
    - 增加了自动清理旧日志的功能。

### 模块 B: 交互式调试实战 (Interactive Debugging)
- **目标**: 体验使用 ADK Web UI 定位问题。
- **产出**: 创建 `research_agent` 并植入故意设计的 Bug。
- **亮点**:
    - 验证了 Traces (链路追踪) 在定位工具参数错误时的价值。
    - 观察到了 LLM 的“自我修正”能力。

### 模块 C: 生产级插件开发 (Production Plugins)
- **目标**: 实现无侵入式的监控代码。
- **产出**:
    - 集成官方 `LoggingPlugin`。
    - 开发自定义 `TelemetryPlugin` (`src/plugins/telemetry_plugin.py`)。
- **亮点**:
    - 实现了对 Agent 运行次数、工具调用、LLM 请求的自动化统计。
    - 采用 AOP (面向切面) 思想，与业务逻辑完全解耦。

## 3. 遇到的问题与解决方案 (Challenges & Solutions)

### 🔴 问题 1: ADK Web UI 找不到智能体
- **现象**: 运行 `adk web research_agent` 后，Web 界面显示 "No agents found"。
- **根本原因 (Root Cause)**: `adk web` 命令的设计逻辑是扫描“工作区目录”下的子文件夹，而不是直接指定单个智能体文件夹。
- **解决方案**:
    - 在项目根目录 (`D:\Agents\my_google_agent`) 直接运行 `adk web`。
    - ADK 成功扫描到 `research_agent` 和 `home_automation_agent`。

### 🟡 问题 2: LLM 掩盖了代码 Bug (Resilience)
- **现象**: `count_papers` 工具的参数类型错误定义为 `str`，导致工具返回了错误的字符计数（如 500），但 Agent 最终回复却给出了正确的论文数量（如 6）。
- **根本原因**: Gemini 2.0 模型具备极强的鲁棒性。它发现工具返回值（500）与它生成的列表内容（6项）严重冲突，因此选择忽略工具输出，使用自己的推理结果。
- **解决方案**:
    - 虽然结果正确，但工程上必须修复。我们将参数类型修正为 `List[str]`，确保工具逻辑的正确性。

### 🔴 问题 3: 插件 API 兼容性报错 (TypeError)
- **现象**: 运行自定义插件时报错 `TypeError: TelemetryPlugin.after_tool_callback() got an unexpected keyword argument...` 以及后续的 `missing required argument...`。
- **根本原因**: 本地安装的 `google-adk` 库版本与教程示例代码的版本不一致。框架在调用回调函数时传递的参数（如 `tool_args`, `callback_context`）发生了变化。
- **解决方案**:
    - 采用**防御性编程**策略。
    - 将回调函数的签名修改为使用 `**kwargs` 接收所有未定义参数：
      ```python
      async def after_tool_callback(self, *, tool: BaseTool, **kwargs: Any) -> None:
      ```
    - 这确保了插件具有**前向兼容性 (Forward Compatibility)**，无论框架未来增加什么参数，插件都不会崩溃。

## 4. 总结与心得

1.  **可观测性分层**: 开发阶段用 Web UI (Traces) 快速定位逻辑错误；生产阶段用 Plugins (Metrics/Logs) 进行宏观监控。
2.  **API 稳定性**: 在使用处于快速迭代期的框架（如 ADK）时，编写插件应尽量使用 `**kwargs` 来应对 API 签名变更。
3.  **模型信任度**: 不要盲目相信 Agent 的最终输出。Agent 可能会“猜对”答案，但中间过程可能是错的。必须通过 Logs 和 Traces 验证执行路径。
