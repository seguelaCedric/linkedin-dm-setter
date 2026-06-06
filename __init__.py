#!/usr/bin/env python3
"""LinkedIn DM Setter plugin for Hermes Agent."""

import sys
from pathlib import Path

# Add plugin data/scripts to path
PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PLUGIN_DIR / "data" / "scripts"))

try:
    from . import schemas, tools
except ImportError:
    import schemas, tools


def register(ctx):
    """Register all tools with Hermes."""
    for schema in schemas.ALL_SCHEMAS:
        ctx.register_tool(
            name=schema["name"],
            toolset="linkedin-dm-setter",
            schema=schema,
            handler=tools.HANDLERS[schema["name"]],
        )
