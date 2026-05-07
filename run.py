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

        # Force server to listen on all interfaces
        # The issue that required this fork was fixed by the author in version `2.17.0`.
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
