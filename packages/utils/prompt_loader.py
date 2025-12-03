"""Reusable prompt loading utility for file-based configuration.

Supports multi-layer fallback for domain-agnostic deployments:
1. Environment variable with full content (quick testing)
2. Environment variable with file path (deployment config)
3. Default file location (convention-based)
4. Built-in default (fallback)
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_prompt(
    default_prompt: str,
    prompt_name: str = "prompt",
    env_var_content: Optional[str] = None,
    env_var_file: Optional[str] = None,
    default_path: Optional[Path] = None,
) -> str:
    """Load prompt from file with multi-layer fallback.

    Search order:
    1. Environment variable with full content (env_var_content)
    2. Environment variable with file path (env_var_file)
    3. Default file location (default_path)
    4. Built-in default prompt

    Args:
        default_prompt: Fallback prompt if no files found
        prompt_name: Name for logging (e.g., "system_prompt", "query_expansion")
        env_var_content: Environment variable name for full prompt content
        env_var_file: Environment variable name for file path
        default_path: Default file location to check

    Returns:
        Loaded prompt text
    """
    # 1. Try env var with full content (for quick testing)
    if env_var_content:
        if content := os.getenv(env_var_content):
            logger.info(f"Loaded {prompt_name} from env var: {env_var_content}")
            return content

    # Build search paths
    search_paths: list[Path] = []

    # 2. Env var for file path
    if env_var_file:
        if file_path := os.getenv(env_var_file):
            search_paths.append(Path(file_path))

    # 3. Default location
    if default_path:
        search_paths.append(default_path)

    # Try each path
    for path in search_paths:
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                logger.info(f"Loaded {prompt_name} from file: {path}")
                return content
            except Exception as e:
                logger.warning(f"Failed to read {prompt_name} from {path}: {e}")

    # 4. Fallback to default
    logger.info(f"Using built-in default {prompt_name} (no custom file found)")
    return default_prompt


@lru_cache()
def load_json_config(
    config_name: str,
    default_path: Path,
    env_var_file: Optional[str] = None,
) -> dict:
    """Load JSON configuration from file with caching.

    Args:
        config_name: Name for logging
        default_path: Default file location
        env_var_file: Environment variable for custom file path

    Returns:
        Parsed JSON as dict, or empty dict on failure
    """
    import json

    search_paths: list[Path] = []

    if env_var_file:
        if file_path := os.getenv(env_var_file):
            search_paths.append(Path(file_path))

    search_paths.append(default_path)

    for path in search_paths:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                logger.info(f"Loaded {config_name} from file: {path}")
                return data
            except Exception as e:
                logger.warning(f"Failed to read {config_name} from {path}: {e}")

    logger.info(f"No {config_name} file found, using empty config")
    return {}
