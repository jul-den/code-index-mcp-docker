#!/usr/bin/env python
"""
Docker-aware entrypoint for code-index-mcp.
- If running inside a container with HTTP transport: configure host=0.0.0.0 and read settings from env.
- Otherwise: delegate to the original main() for local usage.
"""

import os
import sys
import logging


# Add src/ to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from code_index_mcp.server import main as original_main
from code_index_mcp.server import logger, mcp


def is_docker() -> bool:
    """Detect if we are running inside a Docker container."""
    if os.path.exists("/.dockerenv"):
        return True
    try:
        with open("/proc/1/cgroup", "rt") as f:
            if "docker" in f.read() or "kubepods" in f.read():
                return True
    except Exception:
        pass
    return False

def _setup_docker_logging():
    """Настройка логирования для Docker: INFO и выше -> stdout."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    stdout_handler = logging.StreamHandler(sys.stdout)
    
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(logging.INFO)  
    
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(logging.DEBUG)    
    logging.info("Docker logging configured: INFO and above will be printed to stdout")

def get_env(key: str, default=None):
    """
    Get environment variable, supporting both MCP_ prefixed and non-prefixed.
    Example: get_env('PROJECT_PATH') will look for MCP_PROJECT_PATH first,
    then PROJECT_PATH.
    """
    val = os.environ.get(f'MCP_{key}', os.environ.get(key, default))
    # Boolean handling (if default is bool)
    if isinstance(default, bool):
        if val is None:
            return default
        return str(val).lower() in ('true', '1', 'yes')
    return val


def build_argv_from_env() -> list[str]:
    """Build command line arguments from environment variables."""
    args = []
    # Map from environment variable suffix (without MCP_) to CLI argument name
    env_map = {
        "PROJECT_PATH": "--project-path",
        "TRANSPORT": "--transport",
        "MOUNT_PATH": "--mount-path",
        "INDEXER_PATH": "--indexer-path",
        "TOOL_PREFIX": "--tool-prefix",
    }
    for env_suffix, arg_name in env_map.items():
        value = get_env(env_suffix)
        if value:
            args.append(arg_name)
            args.append(str(value))

    # Port handling
    port_str = get_env("PORT")
    if port_str is not None and str(port_str).isdigit():
        args.append("--port")
        args.append(str(port_str))
    return args


def main():
    transport = get_env("TRANSPORT", "stdio")
    inside_docker = is_docker()
    is_http = transport in ("sse", "streamable-http")

    if inside_docker:
        """Entry point when running inside a container with HTTP transport."""
        _setup_docker_logging()
        logger.info("Running inside Docker container")
        # Build argv from environment variables
        argv = build_argv_from_env()
        if argv:
            logger.info("Using arguments from env: %s", argv)
        if is_http:
            # The original Docker issue was fixed upstream in v2.17.0.
            # logger.info("Aapplying 0.0.0.0 binding and env config")
            # Force server to listen on all interfaces
            # mcp.settings.host = "0.0.0.0"

            import json
            import signal
            import subprocess
            import tempfile
            import os
            from typing import Any, Callable, Dict, Optional
            from src.code_index_mcp.utils.error_handler import handle_mcp_tool_errors
            from mcp.server.fastmcp import Context

            # ------------------------------------------------------------
            # Helper: get tool by name from FastMCP registry
            # ------------------------------------------------------------
            def _get_tool_by_name(name: str) -> Optional[Callable]:
                """Retrieve a registered MCP tool function by its name."""
                # FastMCP stores tools in _tool_manager._tools (dict name -> tool)
                if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
                    tool_registry = mcp._tool_manager._tools
                elif hasattr(mcp, "_tools"):
                    tool_registry = mcp._tools
                else:
                    logger.error("Cannot locate tool registry in FastMCP")
                    return None
            
                if name in tool_registry:
                    return tool_registry[name].fn  # .fn is the actual function
                return None
            
            
            # ------------------------------------------------------------
            # Sandbox execution of user code
            # ------------------------------------------------------------
            def _execute_in_sandbox(code: str, data: Any, timeout_seconds: int = 10) -> Dict:
                """
                Execute user-provided Python code in a subprocess with time and memory limits.
                The code must define a function `process(data)` that returns a JSON-serializable value.
                Returns a dict with either 'result' or 'error'.
                """
                # Build script lines without any leading whitespace
                script_lines = [
                    "import json, sys, traceback",
                    "",
                    "# User code",
                    code,
                    "",
                    "# Input data",
                    "data = json.loads(sys.stdin.read())",
                    "",
                    "try:",
                    "    result = process(data)",
                    "    # Ensure result is JSON serializable",
                    "    json.dumps(result)",
                    "    print(json.dumps(result))",
                    "except Exception as e:",
                    "    print(json.dumps({'error': str(e), 'traceback': traceback.format_exc()}), file=sys.stderr)",
                    "    sys.exit(1)",
                ]
                script = "\n".join(script_lines)
            
                # Write script to a temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(script)
                    tmp_path = f.name
            
                try:
                    proc = subprocess.run(
                        ['python', tmp_path],
                        input=json.dumps(data),
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                        env={'PATH': os.environ.get('PATH', '')}
                    )
                    if proc.returncode != 0:
                        try:
                            err = json.loads(proc.stderr)
                            return {"error": err.get("error", "Execution failed")}
                        except json.JSONDecodeError:
                            return {"error": f"Execution failed: {proc.stderr.strip()}"}
                    try:
                        result = json.loads(proc.stdout.strip())
                        return {"result": result}
                    except json.JSONDecodeError:
                        return {"error": f"Invalid JSON output: {proc.stdout.strip()}"}
                except subprocess.TimeoutExpired:
                    return {"error": f"Code execution timed out after {timeout_seconds} seconds"}
                except Exception as e:
                    return {"error": f"Sandbox error: {str(e)}"}
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

            # ------------------------------------------------------------
            # The universal tool: process_tool_result
            # ------------------------------------------------------------
            @mcp.tool()
            @handle_mcp_tool_errors(return_type="dict")
            def process_tool_result(
                tool_name: str,
                tool_args: dict,
                code: str,
                ctx: Context = None
            ) -> dict:
                """
                Call another MCP tool, then process its result with user‑provided Python code.
            
                Args:
                    tool_name: Name of the tool to call (e.g., "find_files", "search_code_advanced").
                    tool_args: Arguments to pass to that tool (as a JSON object).
                    code: Python code that defines a function `process(data)`. The `data` parameter
                          will receive the result of the tool call. The function must return a
                          JSON‑serializable value (e.g., dict, list, str, int, float, bool, None).
            
                Returns:
                    A dict containing either:
                    - `result`: the processed value from `process(data)`
                    - `error`: an error description if something failed
                """
                logger.info(f"process_tool_result: calling '{tool_name}' with args {tool_args}")
            
                # 1. Look up the tool
                tool_func = _get_tool_by_name(tool_name)
                if tool_func is None:
                    return {"error": f"Tool '{tool_name}' not found. Available tools: {list(_get_tool_by_name.__closure__)}"}
            
                # 2. Call the tool
                try:
                    # Tools may expect a Context parameter; if the tool accepts `ctx`, we pass it.
                    # Simple approach: try with ctx, then without.
                    import inspect
                    sig = inspect.signature(tool_func)
                    if 'ctx' in sig.parameters:
                        raw_result = tool_func(**tool_args, ctx=ctx)
                    else:
                        raw_result = tool_func(**tool_args)
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}", exc_info=True)
                    return {"error": f"Tool execution failed: {str(e)}"}
            
                # 3. Execute user code in sandbox
                sandbox_result = _execute_in_sandbox(code, raw_result, timeout_seconds=10)
                return sandbox_result

        else:
            logger.info("Running inside Docker but transport is 'stdio' – using original main()")
        # Call the original main with the constructed arguments
        original_main(argv if argv else None)
    else:
        if not inside_docker:
            logger.info("Not running inside a container – using original main()")
        else:
            logger.info("Running inside Docker but transport is 'stdio' – using original main()")
        original_main()


if __name__ == "__main__":
    main()
