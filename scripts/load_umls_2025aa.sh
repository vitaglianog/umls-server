#!/bin/bash

# Final corrected script to load UMLS 2025AA data
# Fixes: proper file handling, table truncation, and error detection

set -e

echo "🏥 UMLS 2025AA Data Loading Script (Final)"
echo "=========================================="
echo "Loading UMLS Spring 2025 Base Release (2025AA)"
echo ""

# Configuration
CONTAINER_NAME="umls-mysql"
DB_NAME="umls"
DB_USER="umls_user"
DB_PASSWORD="umls_password_secure_2024"
UMLS_DATA_DIR="umls-data/2025AA/META"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Docker Compose is running
echo -n "🐳 Checking MySQL container... "
if ! docker compose ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}❌ MySQL container is not running${NC}"
    echo "Please start with: docker compose up -d mysql"
    exit 1
fi
echo -e "${GREEN}✅ Running${NC}"

# Ensure local_infile is enabled globally
echo -n "🔧 Configuring MySQL for data loading... "
docker exec $CONTAINER_NAME mysql -u root -pumls_root_password_2024 -e "SET GLOBAL local_infile = 1;" &>/dev/null
echo -e "${GREEN}✅${NC}"

# Clean up temp files
echo -n "🧹 Cleaning temporary files... "
docker exec $CONTAINER_NAME bash -c "rm -f /tmp/*.RRF /tmp/*.rrf" &>/dev/null
echo -e "${GREEN}✅${NC}"

# Enhanced function to load data files
load_data_file_final() {
    local table_name=$1
    local file_name=$2
    local description="$3"
    local file_path="$UMLS_DATA_DIR/$file_name"
    
    echo ""
    echo -e "${BLUE}📊 Loading $description...${NC}"
    echo "   Table: $table_name"
    echo "   File: $file_name"
    
    # Check source file
    if [ ! -f "$file_path" ]; then
        echo -e "   ${RED}❌ Source file not found: $file_path${NC}"
        return 1
    fi
    
    local source_size=$(ls -lh "$file_path" | awk '{print $5}')
    echo "   Source size: $source_size"
    
    # Copy file to container with unique name
    local container_file="/tmp/${table_name}_load.RRF"
    echo -n "   Copying to container... "
    if docker cp "$file_path" "$CONTAINER_NAME:$container_file" &>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌ Copy failed${NC}"
        return 1
    fi
    
    # Verify file in container
    echo -n "   Verifying copy... "
    local container_size=$(docker exec $CONTAINER_NAME stat -c%s "$container_file" 2>/dev/null || echo "0")
    local source_bytes=$(stat -f%z "$file_path" 2>/dev/null || echo "0")
    
    if [ "$container_size" -eq "$source_bytes" ]; then
        # Format size in a cross-platform way
        local size_mb=$((container_size / 1024 / 1024))
        echo -e "${GREEN}✅ (${size_mb}MB)${NC}"
    else
        echo -e "${RED}❌ Size mismatch: expected $source_bytes, got $container_size${NC}"
        return 1
    fi
    
    # Truncate table before loading
    echo -n "   Truncating table... "
    if docker exec $CONTAINER_NAME mysql --local-infile=1 -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "TRUNCATE TABLE $table_name;" &>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌ Truncate failed${NC}"
        return 1
    fi
    
    # Load data
    echo -n "   Loading data... "
    local start_time=$(date +%s)
    
    local load_sql="
    SET SESSION sql_mode = '';
    LOAD DATA LOCAL INFILE '$container_file' 
    INTO TABLE $table_name 
    FIELDS TERMINATED BY '|' 
    ESCAPED BY '' 
    LINES TERMINATED BY '\n';"
    
    if docker exec $CONTAINER_NAME mysql --local-infile=1 -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "$load_sql" &>/dev/null; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Get record count
        local count=$(docker exec $CONTAINER_NAME mysql --local-infile=1 -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) FROM $table_name;" 2>/dev/null | tail -n 1)
        echo -e "${GREEN}✅ ($(printf "%'d" $count) records in ${duration}s)${NC}"
        
        # Clean up temp file
        docker exec $CONTAINER_NAME rm -f "$container_file" &>/dev/null
        return 0
    else
        echo -e "${RED}❌ Load failed${NC}"
        return 1
    fi
}

# Show data file summary
echo ""
echo -e "${BLUE}📋 Data Files Summary:${NC}"
for file in "MRCONSO.RRF" "MRDEF.RRF" "MRHIER.RRF" "MRREL.RRF" "MRSTY.RRF" "MRSAT.RRF"; do
    if [ -f "$UMLS_DATA_DIR/$file" ]; then
        size=$(ls -lh "$UMLS_DATA_DIR/$file" | awk '{print $5}')
        echo "   ✅ $file: $size"
    else
        echo "   ❌ $file: Not found"
    fi
done

echo ""
read -p "Continue with data loading? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

echo ""
echo "🚀 Starting UMLS data loading..."

# Load core tables
if load_data_file_final "MRCONSO" "MRCONSO.RRF" "concepts and sources"; then
    echo ""
    echo -e "${GREEN}🎉 MRCONSO loaded successfully!${NC}"
    
    echo ""
    read -p "Continue with remaining tables? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        
        # Load remaining core tables
        load_data_file_final "MRDEF" "MRDEF.RRF" "definitions"
        load_data_file_final "MRHIER" "MRHIER.RRF" "hierarchical relationships" 
        load_data_file_final "MRREL" "MRREL.RRF" "concept relationships"
        
        # Optional tables
        if [ -f "$UMLS_DATA_DIR/MRSTY.RRF" ]; then
            echo ""
            read -p "Load semantic types (MRSTY)? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                load_data_file_final "MRSTY" "MRSTY.RRF" "semantic types"
            fi
        fi
        
        if [ -f "$UMLS_DATA_DIR/MRSAT.RRF" ]; then
            echo ""
            echo -e "${YELLOW}⚠️  MRSAT is 8.8GB and takes 1-3 hours to load${NC}"
            read -p "Load attributes (MRSAT)? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                load_data_file_final "MRSAT" "MRSAT.RRF" "attributes"
            fi
        fi
    fi
else
    echo ""
    echo -e "${RED}❌ MRCONSO loading failed. Please check the error details above.${NC}"
    exit 1
fi

echo ""
echo "🔍 Creating essential indexes..."
docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "
CREATE INDEX IF NOT EXISTS idx_mrconso_cui ON MRCONSO(CUI);
CREATE INDEX IF NOT EXISTS idx_mrconso_sab ON MRCONSO(SAB);
CREATE INDEX IF NOT EXISTS idx_mrconso_str ON MRCONSO(STR(255));
CREATE INDEX IF NOT EXISTS idx_mrdef_cui ON MRDEF(CUI);
CREATE INDEX IF NOT EXISTS idx_mrhier_cui ON MRHIER(CUI);
CREATE INDEX IF NOT EXISTS idx_mrrel_cui1 ON MRREL(CUI1);
CREATE INDEX IF NOT EXISTS idx_mrrel_cui2 ON MRREL(CUI2);
" &>/dev/null

echo ""
echo -e "${GREEN}🎉 UMLS 2025AA loading completed successfully!${NC}"
echo ""
echo "📊 Final database statistics:"
docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "
SELECT 
    TABLE_NAME as 'Table',
    TABLE_ROWS as 'Records',
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = '$DB_NAME' 
AND TABLE_NAME LIKE 'MR%'
ORDER BY TABLE_ROWS DESC;
"

echo ""
echo -e "${GREEN}🚀 Ready to start API!${NC}"
echo "Next: docker compose up -d umls-api" 