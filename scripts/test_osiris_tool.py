#!/usr/bin/env python3
"""Quick test script for OSIRIS worksite tool.

Usage:
    python scripts/test_osiris_tool.py <worksite_id> [language]

Examples:
    python scripts/test_osiris_tool.py 12345
    python scripts/test_osiris_tool.py 12345 nl
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


from packages.config import settings
from packages.core.tools.osiris_worksite import get_worksite_info
from packages.core.types import RAGContext


async def test_osiris_tool():
    """Test OSIRIS worksite tool with command-line arguments."""

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_osiris_tool.py <worksite_id> [language]")
        print("\nExamples:")
        print("  python scripts/test_osiris_tool.py 12345")
        print("  python scripts/test_osiris_tool.py 12345 nl")
        sys.exit(1)

    worksite_id = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "fr"

    # Create minimal RAGContext (we don't need DB for this test)
    # Mock SupabaseRestClient since we're not using it for worksite queries
    class MockSupabaseClient:
        pass

    rag_context = RAGContext(
        db_client=MockSupabaseClient(),  # type: ignore
        osiris_config=settings.osiris,
    )

    # Create mock RunContext
    class MockRunContext:
        def __init__(self, deps):
            self.deps = deps

    ctx = MockRunContext(deps=rag_context)

    # Test the tool
    print("\n🔍 Testing OSIRIS worksite tool:")
    print(f"   Worksite ID: {worksite_id}")
    print(f"   Language: {language}")
    print(f"   API URL: {settings.osiris.base_url}")
    print(f"   Username: {settings.osiris.username}")
    print(f"   Password configured: {'✅' if settings.osiris.password else '❌'}")
    print()

    result = await get_worksite_info(ctx, worksite_id=worksite_id, language=language)  # type: ignore

    print("📋 Result:")
    print(result)
    print()


if __name__ == "__main__":
    asyncio.run(test_osiris_tool())
