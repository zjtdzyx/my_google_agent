# Project Review: Multi-Agent Architectures Implementation

**Date:** December 3, 2025  
**Context:** Implementation of Google ADK "Day 1b: Agent Architectures" tutorial.

## 1. Overview

The goal of this session was to transition from single-agent systems to sophisticated **Multi-Agent Architectures**. We successfully implemented four distinct patterns, moving from dynamic orchestration to deterministic pipelines and self-correcting loops.

## 2. Implemented Modules

We structured the implementation into four standalone modules within `multi_agent_demos/`:

### Module 1: The Manager (Dynamic Orchestration)
-   **File**: `01_manager_agent.py`
-   **Pattern**: **LLM Orchestrator**. A root agent uses other agents as tools.
-   **Key Learning**: How to wrap agents using `AgentTool` and pass data implicitly via `output_key`.
-   **Use Case**: Complex queries requiring dynamic decision-making (e.g., "Do I need to search for this?").

### Module 2: The Pipeline (Deterministic Workflow)
-   **File**: `02_sequential_pipeline.py`
-   **Pattern**: **SequentialAgent**. A linear assembly line (A $\to$ B $\to$ C).
-   **Key Learning**: Context injection using placeholders like `{blog_outline}` in prompts.
-   **Use Case**: Standard Operating Procedures (SOPs) like Blog Writing (Outline $\to$ Write $\to$ Edit).

### Module 3: The Parallel Processor (Concurrent Execution)
-   **File**: `03_parallel_processor.py`
-   **Pattern**: **ParallelAgent**. Map-Reduce style execution.
-   **Key Learning**: Running multiple agents simultaneously to reduce latency, then aggregating results.
-   **Use Case**: Multi-domain research (Tech + Health + Finance) summarized into one report.

### Module 4: The Refiner (Self-Correction Loop)
-   **File**: `04_loop_refiner.py`
-   **Pattern**: **LoopAgent**. Iterative refinement.
-   **Key Learning**: Using `FunctionTool` to trigger an exit condition (`exit_loop`) based on LLM judgment.
-   **Use Case**: Quality assurance, such as a Writer/Critic loop that runs until "APPROVED".

## 3. Troubleshooting Log

During implementation, we encountered and resolved specific engineering challenges related to the ADK version.

### 🔴 Issue 1: API Signature Mismatch
**Error**: `TypeError: Runner.run() takes 1 positional argument but 2 were given`  
**Context**: Occurred when calling `runner.run(user_query)` in Module 1.  
**Root Cause**: The installed version of `google-adk` (Preview) has a different signature for `InMemoryRunner.run()`, or it strictly enforces keyword arguments. Additionally, the tutorial context suggested `run_debug` for interactive traces.  
**Solution**: Switched to `await runner.run_debug(user_query)`, aligning with the pattern found in `run_with_plugins.py`.

### 🔴 Issue 2: Return Type Handling
**Error**: `AttributeError: 'list' object has no attribute 'text'`  
**Context**: Occurred when trying to print `response.text` after switching to `run_debug`.  
**Root Cause**: Unlike `run()`, which returns a single Response object, `run_debug()` returns a **List of StepResults** (a trace of the entire execution chain).  
**Solution**: Implemented a robust result extraction logic:
```python
if isinstance(response, list) and response:
    # Extract the last step's text
    last_step = response[-1]
    print(getattr(last_step, 'text', str(last_step)))
else:
    print(getattr(response, 'text', str(response)))
```

## 4. Engineering Best Practices Applied

To ensure the code is "Production-Ready" rather than just "Tutorial-Grade", we applied the following:

1.  **Centralized Configuration**:
    -   Instead of hardcoding API keys, we imported `config.settings` to load from `.env`.
    -   Standardized Model Name (`gemini-2.0-flash-lite-preview-02-05`) across all files.

2.  **Structured Logging**:
    -   Replaced `print()` statements with `logging.getLogger()`.
    -   Used `settings.setup_logging()` to ensure logs are written to both Console and File.

3.  **Resilience**:
    -   Configured `HttpRetryOptions` for all Gemini models to handle transient 429/500 errors.
    -   Added `try-except` blocks around the main execution logic.

4.  **Type Safety**:
    -   Added Python Type Hints (e.g., `-> Agent`) to all factory functions for better IDE support.

## 5. Next Steps
-   **Deployment**: Containerize these agents using the `Dockerfile` provided in the workspace.
-   **Observability**: Integrate `TelemetryPlugin` (from `src/plugins`) to track token usage and latency across these new architectures.
