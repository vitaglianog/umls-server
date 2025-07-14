#!/bin/bash

echo "🚀 UMLS Database Performance Optimization"
echo "=========================================="
echo "This script will add strategic indices to optimize API query performance"
echo "Note: Only creates indices not already provided by official UMLS scripts"
echo ""

# Check if running from main load script
if [ "$1" = "--from-load-script" ]; then
    echo "Running as part of main UMLS loading process..."
    echo ""
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="umls-mysql"

# Load database configuration from .env file
if [ -f ".env" ]; then
    echo "📋 Loading database configuration from .env file..."
    export $(grep -v '^#' .env | xargs)
    DB_NAME="${DB_NAME:-umls}"
    DB_USER="${DB_USER:-umls_user}"
    DB_PASSWORD="${DB_PASSWORD:-umls_password}"
    MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-umls_root_password}"
    echo "   Database: $DB_NAME"
    echo "   User: $DB_USER"
    echo "   Host: ${DB_HOST:-localhost}"
else
    echo "⚠️  No .env file found, using defaults"
    DB_NAME="umls"
    DB_USER="umls_user"
    DB_PASSWORD="umls_password"
    MYSQL_ROOT_PASSWORD="umls_root_password"
fi
echo ""

# Check if containers are running
echo "🔍 Pre-flight checks..."
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ MySQL container not running. Start with: docker-compose up -d${NC}"
    exit 1
fi

echo -e "${GREEN}✅ MySQL container is running${NC}"

# Test database connection
echo -n "🔐 Testing database connection... "
if docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT 1;" &>/dev/null; then
    echo -e "${GREEN}✅ Connected successfully${NC}"
else
    echo -e "${RED}❌ Cannot connect to database${NC}"
    echo "Please check your database credentials in .env file"
    exit 1
fi

# Check for blocking queries
echo "🔍 Checking for blocking queries..."
blocking_queries=$(docker exec $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD -e "SHOW PROCESSLIST;" 2>/dev/null | grep -c "executing" || echo "0")
blocking_queries=$(echo "$blocking_queries" | tr -d '\n\r' | head -c 1)

if [[ $blocking_queries -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Found $blocking_queries active queries that may block index creation${NC}"
    echo "Recommendation: Stop Claude Desktop and other API clients first"
    read -p "Continue anyway? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Optimization cancelled. Stop API clients and try again."
        exit 0
    fi
fi

# Show current performance baseline  
echo "📊 Current Performance Baseline:"
echo "--------------------------------"
docker exec $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME -e "
SELECT 
    TABLE_NAME, 
    TABLE_ROWS, 
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size_MB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = '$DB_NAME' 
AND TABLE_NAME IN ('MRCONSO', 'MRHIER', 'MRDEF')
ORDER BY TABLE_ROWS DESC;" 2>/dev/null

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT CONSIDERATIONS:${NC}"
echo "• This will create additional API-optimized indices (non-duplicates)"
echo "• Only creates indices not already provided by official UMLS scripts"
echo "• Estimated time: 5-15 minutes"
echo "• Temporary increased CPU/memory usage during creation"  
echo "• API will remain available during optimization"
echo ""

read -p "Do you want to proceed with optimization? (y/N): " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Optimization cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}🔧 Starting Database Optimization (API-Focused)...${NC}"
echo ""

# Record start time
start_time=$(date)
echo "⏱️  Started: $start_time"

# Function to run SQL and check success
run_sql() {
    local sql="$1"
    local description="$2"
    
    echo -e "${BLUE}🔨 $description${NC}"
    
    # Use -i flag and pipe the SQL directly
    result=$(echo "$sql" | docker exec -i $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME 2>&1)
    local exit_code=$?
    
    # Check if it's just a "duplicate key" error (index already exists)
    if [[ $exit_code -eq 1 && "$result" == *"Duplicate key name"* ]]; then
        echo -e "${YELLOW}  ⚠️  Index already exists (skipping)${NC}"
        return 0
    elif [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}  ✅ Success${NC}"
        return 0
    else
        echo -e "${RED}  ❌ Failed: $result${NC}"
        return 1
    fi
}

# Check if official UMLS indices are already created
echo "🔍 Checking for official UMLS indices..."
official_indices=$(docker exec $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME -e "
SELECT COUNT(*) FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = '$DB_NAME' 
AND INDEX_NAME LIKE 'X_MR%';" 2>/dev/null | tail -n 1)

if [[ $official_indices -gt 0 ]]; then
    echo -e "${GREEN}✅ Found $official_indices official UMLS indices${NC}"
    echo "🎯 Creating additional performance indices (non-duplicates)..."
    echo ""
    
    # Only create indices that provide additional value beyond official ones
    # Most official indices already exist, so focus on API-specific optimizations
    
    # 1. Compound index for API term searches (SAB + STR prefix)
    run_sql "CREATE INDEX idx_api_sab_str_prefix ON MRCONSO(SAB, STR(100));" \
            "Creating API-optimized SAB+STR prefix index (for term searches)"
    
    # 2. Compound index for CUI + SAB lookups (common in API)
    run_sql "CREATE INDEX idx_api_cui_sab ON MRCONSO(CUI, SAB);" \
            "Creating API-optimized CUI+SAB index (for filtered lookups)"
    
    # 3. MRREL relationship optimization for similarity queries
    run_sql "CREATE INDEX idx_api_mrrel_rel_cui ON MRREL(REL, CUI1, CUI2);" \
            "Creating API-optimized relationship index (for similarity queries)"
    
else
    echo -e "${YELLOW}⚠️  Official UMLS indices not found${NC}"
    echo "This suggests the official mysql_indexes.sql was not run."
    echo "Please run the main load script first: ./scripts/load_umls_2025aa.sh"
    echo ""
    echo "Alternatively, create basic indices manually:"
    
    # Create basic indices if official ones don't exist
    run_sql "CREATE INDEX idx_basic_mrconso_cui ON MRCONSO(CUI);" \
            "Creating basic MRCONSO CUI index"
    
    run_sql "CREATE INDEX idx_basic_mrconso_sab_str ON MRCONSO(SAB, STR(50));" \
            "Creating basic MRCONSO SAB+STR index"
    
    run_sql "CREATE INDEX idx_basic_mrhier_cui ON MRHIER(CUI);" \
            "Creating basic MRHIER CUI index"
    
    run_sql "CREATE INDEX idx_basic_mrdef_cui ON MRDEF(CUI);" \
            "Creating basic MRDEF CUI index"
fi

echo ""
echo -e "${GREEN}✅ Index creation completed!${NC}"

# Show results
end_time=$(date)
echo "⏱️  Completed: $end_time"
echo ""

echo "📊 Optimization Results:"
echo "------------------------"
docker exec $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME -e "
SELECT 
    TABLE_NAME, 
    TABLE_ROWS, 
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Total_Size_MB',
    ROUND((INDEX_LENGTH / 1024 / 1024), 2) AS 'Index_Size_MB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = '$DB_NAME' 
AND TABLE_NAME IN ('MRCONSO', 'MRHIER', 'MRDEF')
ORDER BY TABLE_ROWS DESC;" 2>/dev/null

echo ""
echo "🔍 Verify indices were created:"
docker exec $CONTAINER_NAME mysql -u root -p$MYSQL_ROOT_PASSWORD $DB_NAME -e "
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = '$DB_NAME'
AND (INDEX_NAME LIKE 'idx_%' OR INDEX_NAME LIKE 'X_MR%')
ORDER BY TABLE_NAME, INDEX_NAME;" 2>/dev/null

echo ""
echo -e "${GREEN}🎯 Performance Testing:${NC}"
echo "Test your optimized API:"
echo ""
echo "# Fast term search (now optimized):"
echo "curl 'http://localhost:8000/terms?search=diabetes&ontology=HPO'"
echo ""
echo "# Run full benchmark:"
echo "./scripts/benchmark_api.sh"
echo ""

echo -e "${GREEN}🚀 OPTIMIZATION COMPLETE!${NC}"
echo "Additional API-focused indices created (no duplicates with official UMLS indices)"
echo "Expected improvements: Enhanced performance for complex API queries!" 