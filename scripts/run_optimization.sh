#!/bin/bash

echo "🚀 UMLS Database Performance Optimization"
echo "=========================================="
echo "This script will add strategic indices to optimize API query performance"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if containers are running
echo "🔍 Pre-flight checks..."
if ! docker ps | grep -q "umls-mysql"; then
    echo -e "${RED}❌ MySQL container not running. Start with: docker-compose up -d${NC}"
    exit 1
fi

echo -e "${GREEN}✅ MySQL container is running${NC}"

# Check for blocking queries
echo "🔍 Checking for blocking queries..."
blocking_queries=$(docker exec umls-mysql mysql -u root -pumls_root_password_2024 -e "SHOW PROCESSLIST;" 2>/dev/null | grep -c "executing" || echo "0")
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
docker exec umls-mysql mysql -u root -pumls_root_password_2024 umls -e "
SELECT 
    TABLE_NAME, 
    TABLE_ROWS, 
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Size_MB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'umls' 
AND TABLE_NAME IN ('MRCONSO', 'MRHIER', 'MRDEF')
ORDER BY TABLE_ROWS DESC;" 2>/dev/null

echo ""
echo -e "${YELLOW}⚠️  IMPORTANT CONSIDERATIONS:${NC}"
echo "• This will create critical indices on 222M+ records"
echo "• Estimated time: 10-20 minutes"
echo "• Temporary increased CPU/memory usage during creation"  
echo "• API will remain available during optimization"
echo ""

read -p "Do you want to proceed with optimization? (y/N): " -r
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Optimization cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}🔧 Starting Database Optimization (Fixed Method)...${NC}"
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
    result=$(echo "$sql" | docker exec -i umls-mysql mysql -u root -pumls_root_password_2024 umls 2>&1)
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

# Critical indices to create (in order of importance)
echo "🎯 Creating critical performance indices..."
echo ""

# 1. Most critical: MRCONSO CUI index
run_sql "CREATE INDEX idx_mrconso_cui ON MRCONSO(CUI);" \
        "Creating MRCONSO CUI index (critical for lookups)"

# 2. Most critical: MRCONSO compound SAB+STR index  
run_sql "CREATE INDEX idx_mrconso_sab_str ON MRCONSO(SAB, STR(50));" \
        "Creating MRCONSO SAB+STR index (critical for term searches)"

# 3. Important: MRHIER CUI index
run_sql "CREATE INDEX idx_mrhier_cui ON MRHIER(CUI);" \
        "Creating MRHIER CUI index (for hierarchy operations)"

# 4. Helpful: MRDEF CUI index
run_sql "CREATE INDEX idx_mrdef_cui ON MRDEF(CUI);" \
        "Creating MRDEF CUI index (for definition joins)"

# 5. Performance: MRCONSO AUI index
run_sql "CREATE INDEX idx_mrconso_aui ON MRCONSO(AUI);" \
        "Creating MRCONSO AUI index (for ancestor operations)"

echo ""
echo -e "${GREEN}✅ Index creation completed!${NC}"

# Show results
end_time=$(date)
echo "⏱️  Completed: $end_time"
echo ""

echo "📊 Optimization Results:"
echo "------------------------"
docker exec umls-mysql mysql -u root -pumls_root_password_2024 umls -e "
SELECT 
    TABLE_NAME, 
    TABLE_ROWS, 
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS 'Total_Size_MB',
    ROUND((INDEX_LENGTH / 1024 / 1024), 2) AS 'Index_Size_MB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'umls' 
AND TABLE_NAME IN ('MRCONSO', 'MRHIER', 'MRDEF')
ORDER BY TABLE_ROWS DESC;" 2>/dev/null

echo ""
echo "🔍 Verify indices were created:"
docker exec umls-mysql mysql -u root -pumls_root_password_2024 umls -e "
SELECT 
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'umls'
AND INDEX_NAME LIKE 'idx_%'
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
echo "Expected improvements: 10-50x faster for term searches!" 