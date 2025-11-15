#!/bin/bash

################################################################################
# Parallel Historical Backfill Trigger Script
################################################################################
# 
# This script triggers multiple GitHub Actions workflows in parallel to scrape
# sold properties across different time periods.
#
# Strategy:
# - Split 60 months (2020-2025) into 5 batches of 12 months each
# - Each batch runs in parallel (separate workflow)
# - Each workflow completes in ~1-2 hours (well under 6h limit)
# - Total time: ~2 hours (vs 10+ hours sequential)
#
# Requirements:
# - GitHub CLI (gh) installed: brew install gh
# - Authenticated: gh auth login
#
# Usage:
#   ./scripts/trigger_backfill_parallel.sh
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not found${NC}"
    echo "Install with: brew install gh"
    echo "Then authenticate: gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not authenticated with GitHub${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Historical Sold Properties Backfill - Parallel Trigger  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Define batches (12 months each, fits in ~1-2 hours)
# Adjusted to stay well under 6-hour limit with safety margin
declare -a BATCHES=(
    "2020-01:2020-12"  # Batch 1: Year 2020
    "2021-01:2021-12"  # Batch 2: Year 2021
    "2022-01:2022-12"  # Batch 3: Year 2022
    "2023-01:2023-12"  # Batch 4: Year 2023
    "2024-01:2024-12"  # Batch 5: Year 2024
    "2025-01:2025-11"  # Batch 6: Year 2025 (up to Nov)
)

echo -e "${YELLOW}📋 Backfill Plan:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for i in "${!BATCHES[@]}"; do
    IFS=':' read -r start end <<< "${BATCHES[$i]}"
    echo "  Batch $((i+1)): $start to $end"
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Confirm with user
read -p "🚀 Trigger all batches in parallel? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⚠️  Cancelled by user${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 Triggering workflows...${NC}"
echo ""

# Track workflow IDs
declare -a WORKFLOW_IDS=()

# Trigger each batch
for i in "${!BATCHES[@]}"; do
    IFS=':' read -r start end <<< "${BATCHES[$i]}"
    
    echo -e "${BLUE}→ Triggering Batch $((i+1)):${NC} $start to $end"
    
    # Trigger workflow and capture output
    OUTPUT=$(gh workflow run scrape_sold_batch.yml \
        -f start_month="$start" \
        -f end_month="$end" \
        -f max_pages=50 2>&1)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Triggered successfully${NC}"
        
        # Wait a bit to get workflow ID
        sleep 2
        
        # Get the most recent workflow run
        RUN_ID=$(gh run list --workflow=scrape_sold_batch.yml --limit 1 --json databaseId --jq '.[0].databaseId')
        
        if [ -n "$RUN_ID" ]; then
            WORKFLOW_IDS+=("$RUN_ID")
            echo -e "${BLUE}  🔗 Run ID: $RUN_ID${NC}"
            echo -e "${BLUE}  📍 URL: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/actions/runs/$RUN_ID${NC}"
        fi
    else
        echo -e "${RED}  ✗ Failed to trigger${NC}"
        echo "  Error: $OUTPUT"
    fi
    
    # Small delay between triggers to avoid rate limits
    sleep 3
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All workflows triggered!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Display summary
echo -e "${YELLOW}📊 Summary:${NC}"
echo "  Total batches: ${#BATCHES[@]}"
echo "  Workflows triggered: ${#WORKFLOW_IDS[@]}"
echo "  Expected completion: ~1-2 hours"
echo ""

# Monitor option
echo -e "${BLUE}📈 Monitor Progress:${NC}"
echo ""
echo "  View all runs:"
echo "    gh run list --workflow=scrape_sold_batch.yml"
echo ""
echo "  Watch specific run:"
echo "    gh run watch <RUN_ID>"
echo ""
echo "  View logs:"
echo "    gh run view <RUN_ID> --log"
echo ""

# Offer to watch workflows
read -p "👀 Watch workflow progress? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}📊 Monitoring all workflows...${NC}"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
    
    while true; do
        echo -e "\n${YELLOW}━━━ Status Update ($(date '+%H:%M:%S')) ━━━${NC}\n"
        
        # Get status of all runs
        gh run list --workflow=scrape_sold_batch.yml --limit ${#BATCHES[@]} \
            --json number,status,conclusion,startedAt,displayTitle \
            --template '{{range .}}{{printf "Run #%-3d" .number}} | {{printf "%-12s" .status}} | {{.displayTitle}}{{"\n"}}{{end}}'
        
        # Check if all completed
        RUNNING=$(gh run list --workflow=scrape_sold_batch.yml --limit ${#BATCHES[@]} --json status --jq '[.[] | select(.status=="in_progress" or .status=="queued")] | length')
        
        if [ "$RUNNING" -eq 0 ]; then
            echo ""
            echo -e "${GREEN}🎉 All workflows completed!${NC}"
            break
        fi
        
        sleep 30
    done
fi

echo ""
echo -e "${GREEN}✨ Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Check workflow results in GitHub Actions"
echo "  2. Verify all months collected: ls -l data/raw/sold_links/"
echo "  3. Tomorrow: Run property detail scraper"
