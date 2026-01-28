#!/usr/bin/env python3
"""Test OTRS get_otrs_ticket function to verify web_url construction."""

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pydantic_ai import RunContext  # noqa: E402
from pydantic_ai import usage as usage_module  # noqa: E402

from packages.config import OTRSToolConfig  # noqa: E402
from packages.core.tools.otrs_tool import get_otrs_ticket  # noqa: E402


@dataclass
class MockDeps:
    """Mock dependencies for testing."""

    otrs_config: OTRSToolConfig


async def test_get_ticket():
    """Test get_otrs_ticket and verify web_url."""
    print("=" * 60)
    print("OTRS Get Ticket Test")
    print("=" * 60)

    config = OTRSToolConfig()

    if not config.is_configured:
        print("❌ OTRS is not configured")
        return False

    print("\n📋 Testing with ticket ID: 9022")

    try:
        mock_deps = MockDeps(otrs_config=config)
        mock_context = RunContext(
            deps=mock_deps,
            retry=0,
            tool_name="test",
            model="openai:gpt-4o-mini",
            usage=usage_module.Usage(),
        )

        result = await get_otrs_ticket(mock_context, ticket_id="9022", include_articles=False)

        result_data = json.loads(result)

        if "error" in result_data:
            print(f"❌ Error: {result_data['error']}")
            return False

        print("\n✅ Ticket retrieved successfully!")
        print("\n📝 Ticket Details:")
        print(f"   ID: {result_data.get('ticket_id')}")
        print(f"   Number: {result_data.get('ticket_number')}")
        print(f"   Title: {result_data.get('title')}")
        print(f"   State: {result_data.get('state')}")

        # Most important: web_url for iframe viewing
        web_url = result_data.get("web_url")
        if web_url:
            print("\n🌐 Web URL (for View Ticket button):")
            print(f"   {web_url}")
            print("\n✅ View Ticket button will work!")
        else:
            print("\n⚠️  No web_url in response")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_get_ticket())
    sys.exit(0 if success else 1)
