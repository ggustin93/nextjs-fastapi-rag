#!/bin/bash
# =============================================================================
# repair-migrations.sh - Fix Supabase migration history conflicts
# =============================================================================
# This script repairs migration history when the remote database has
# pre-existing migrations that conflict with new ones.
#
# Usage:
#   ./scripts/repair-migrations.sh "$DATABASE_PASSWORD"
#   ./scripts/repair-migrations.sh "$DATABASE_PASSWORD" --dry-run
#
# What it does:
#   1. Lists current migration status
#   2. Marks old migrations (Nov-Dec 2025) as reverted
#   3. Pushes new HNSW migrations (20260130000001, 20260130000002)
#
# Prerequisites:
#   - supabase CLI installed
#   - Project linked: supabase link --project-ref <your-ref>
#   - DATABASE_URL or password provided
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
DRY_RUN=false
DB_PASSWORD="${1:-}"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
    esac
done

echo -e "${GREEN}=== Supabase Migration Repair Script ===${NC}"
echo ""

# Check supabase CLI
if ! command -v supabase &> /dev/null; then
    echo -e "${RED}Error: supabase CLI not found${NC}"
    echo "Install with: npm install -g supabase"
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check if project is linked
if [ ! -f ".supabase/project-ref" ]; then
    echo -e "${YELLOW}Warning: Project not linked to Supabase${NC}"
    echo "Run: supabase link --project-ref <your-project-ref>"
    echo ""
fi

# Step 1: Show current migration status
echo -e "${GREEN}Step 1: Current migration status${NC}"
echo "-----------------------------------"
supabase migration list --linked 2>/dev/null || echo "Could not list remote migrations (project may not be linked)"
echo ""

# Step 2: Check for conflicting migrations
echo -e "${GREEN}Step 2: Checking for conflicts${NC}"
echo "-----------------------------------"

# List of migrations that may need to be reverted
OLD_MIGRATIONS=(
    "20251115_initial_schema"
    "20251120_add_toc_column"
    "20251125_hybrid_search"
    "20251201_add_fts_indexes"
    "20251210_update_hybrid_search"
)

echo "Migrations that may need repair:"
for migration in "${OLD_MIGRATIONS[@]}"; do
    echo "  - $migration"
done
echo ""

# Step 3: Mark old migrations as reverted (if they exist)
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN: Would mark old migrations as reverted${NC}"
else
    echo -e "${GREEN}Step 3: Marking old migrations as reverted${NC}"
    echo "-----------------------------------"

    # This requires direct database access
    if [ -z "$DB_PASSWORD" ]; then
        echo -e "${YELLOW}Skipping: No database password provided${NC}"
        echo "To repair migrations, run:"
        echo "  ./scripts/repair-migrations.sh \"\$DATABASE_PASSWORD\""
        echo ""
        echo "Or manually run this SQL in Supabase Dashboard > SQL Editor:"
        cat << 'EOF'
-- Mark old migrations as reverted (run if supabase db push fails)
UPDATE supabase_migrations.schema_migrations
SET reverted_at = NOW()
WHERE name IN (
    '20251115_initial_schema',
    '20251120_add_toc_column',
    '20251125_hybrid_search',
    '20251201_add_fts_indexes',
    '20251210_update_hybrid_search'
)
AND reverted_at IS NULL;
EOF
    else
        echo "Connecting to database..."
        # Get DATABASE_URL from environment or construct it
        if [ -n "${DATABASE_URL:-}" ]; then
            DB_URL="$DATABASE_URL"
        else
            echo -e "${YELLOW}DATABASE_URL not set. Skipping direct repair.${NC}"
            echo "Set DATABASE_URL or run SQL manually in Supabase Dashboard."
        fi
    fi
fi
echo ""

# Step 4: Push new migrations
echo -e "${GREEN}Step 4: Pushing new migrations${NC}"
echo "-----------------------------------"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN: Would push these migrations:${NC}"
    ls -la supabase/migrations/*.sql 2>/dev/null || echo "No migrations found"
else
    echo "Pushing migrations to remote database..."
    supabase db push --linked || {
        echo ""
        echo -e "${YELLOW}Migration push failed. This may be due to:${NC}"
        echo "1. Conflicting migration names (run the repair SQL above)"
        echo "2. SQL errors in migration files"
        echo "3. Network issues"
        echo ""
        echo "Try running migrations manually in Supabase Dashboard > SQL Editor:"
        echo "  - supabase/migrations/20260130000001_hnsw_index.sql"
        echo "  - supabase/migrations/20260130000002_hybrid_search_ef_search.sql"
    }
fi
echo ""

# Step 5: Verify
echo -e "${GREEN}Step 5: Verification${NC}"
echo "-----------------------------------"

if [ "$DRY_RUN" = false ]; then
    echo "Final migration status:"
    supabase migration list --linked 2>/dev/null || echo "Could not verify (project may not be linked)"

    echo ""
    echo "To verify HNSW index exists, run this SQL in Supabase Dashboard:"
    cat << 'EOF'
-- Check HNSW index exists
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'chunks' AND indexname LIKE '%hnsw%';

-- Check hybrid_search has ef_search parameter
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'hybrid_search';
EOF
fi

echo ""
echo -e "${GREEN}=== Done ===${NC}"
