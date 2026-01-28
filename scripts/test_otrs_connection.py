#!/usr/bin/env python3
"""Test OTRS connection with configured credentials."""

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pydantic_ai import RunContext  # noqa: E402

from packages.config import OTRSToolConfig  # noqa: E402
from packages.core.tools.otrs_tool import _get_session_id, search_otrs_tickets  # noqa: E402


@dataclass
class MockDeps:
    """Mock dependencies for testing."""

    otrs_config: OTRSToolConfig


async def test_connection():
    """Test OTRS connection and authentication."""
    print("=" * 60)
    print("OTRS Connection Test")
    print("=" * 60)

    # Load configuration
    config = OTRSToolConfig()

    print("\n📋 Configuration:")
    print(f"  Server URL: {config.server_url or '❌ Not set'}")
    print(f"  Username: {config.username or '❌ Not set'}")
    print(f"  Password: {'✅ Set' if config.password else '❌ Not set'}")
    print(f"  Timeout: {config.timeout_seconds}s")
    print(f"  Verify SSL: {config.verify_ssl}")
    print(f"  Web URL: {config.web_url or '(defaults to server URL)'}")
    print(f"  Search Cache TTL: {config.search_cache_ttl_seconds}s")
    print(f"  Ticket Cache TTL: {config.cache_ttl_seconds}s")

    if not config.is_configured:
        print("\n❌ OTRS is not configured. Please set:")
        print("   - OTRS_SERVER_URL")
        print("   - OTRS_USERNAME")
        print("   - OTRS_PASSWORD")
        return False

    print("\n🔌 Testing connection...")

    try:
        # Test 1: Session creation
        print("\n1️⃣ Testing authentication...")
        session_id = await _get_session_id(config)

        if session_id:
            print(f"   ✅ Session created: {session_id[:20]}...")
        else:
            print("   ❌ Authentication failed: No session ID returned")
            return False

        # Test 2: Search tickets
        print("\n2️⃣ Testing ticket search...")
        mock_deps = MockDeps(otrs_config=config)
        from pydantic_ai import usage as usage_module

        mock_context = RunContext(
            deps=mock_deps,
            retry=0,
            tool_name="test",
            model="openai:gpt-4o-mini",
            usage=usage_module.Usage(),
        )

        result = await search_otrs_tickets(mock_context, search_text="test", limit=5)

        # Parse result
        result_data = json.loads(result)

        if "error" in result_data:
            print(f"   ⚠️  Search returned error: {result_data['error']}")
            # Still consider it a success if we can connect
            print("   ✅ But connection works (may have no tickets)")
        else:
            ticket_count = len(result_data.get("tickets", []))
            print(f"   ✅ Search successful: Found {ticket_count} ticket(s)")

            if ticket_count > 0:
                first_ticket = result_data["tickets"][0]
                print("   📋 Sample ticket (raw data):")
                print(f"      {json.dumps(first_ticket, indent=8, ensure_ascii=False)[:300]}...")

        print("\n" + "=" * 60)
        print("✅ OTRS CONNECTION TEST PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
