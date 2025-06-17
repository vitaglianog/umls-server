#!/bin/bash

# Monitor UMLS loading progress and disk usage
# Run this in a separate terminal while loading

echo "🔍 UMLS Loading Monitor"
echo "======================="
echo "Press Ctrl+C to stop monitoring"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

CONTAINER_NAME="umls-mysql"
DB_USER="umls_user"
DB_PASSWORD="umls_password_secure_2024"
DB_NAME="umls"

# Function to get table row count
get_table_count() {
    local table_name=$1
    docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) as count FROM $table_name;" 2>/dev/null | tail -n 1 | tr -d '\n'
}

# Function to check if table exists
table_exists() {
    local table_name=$1
    docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "SHOW TABLES LIKE '$table_name';" 2>/dev/null | grep -q "$table_name"
}

# Function to get database size
get_db_size() {
    docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD $DB_NAME -e "
    SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size (MB)'
    FROM information_schema.tables
    WHERE table_schema = '$DB_NAME';" 2>/dev/null | tail -n 1
}

# Function to get MySQL data directory size
get_mysql_dir_size() {
    docker exec $CONTAINER_NAME du -sh /var/lib/mysql 2>/dev/null | awk '{print $1}'
}

# Function to check MySQL processes
get_mysql_processes() {
    docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -e "
    SELECT COUNT(*) as active_queries 
    FROM information_schema.processlist 
    WHERE command != 'Sleep';" 2>/dev/null | tail -n 1
}

# Function to get current loading process info
get_loading_info() {
    docker exec $CONTAINER_NAME mysql -u$DB_USER -p$DB_PASSWORD -e "
    SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, LEFT(INFO, 50) as QUERY_START
    FROM information_schema.processlist 
    WHERE COMMAND = 'Query' AND INFO IS NOT NULL;" 2>/dev/null
}

while true; do
    clear
    echo -e "${BLUE}🔍 UMLS Loading Monitor - $(date)${NC}"
    echo "=================================================="
    
    # Docker system info
    echo -e "${GREEN}💾 Docker Disk Usage:${NC}"
    docker system df | head -n 5
    echo ""
    
    # Host disk space
    echo -e "${GREEN}🖥️  Host Disk Space:${NC}"
    df -h . | tail -n 1
    echo ""
    
    # MySQL container space
    echo -e "${GREEN}🗄️  MySQL Data Directory:${NC}"
    mysql_size=$(get_mysql_dir_size)
    echo "MySQL data size: $mysql_size"
    echo ""
    
    # Database size
    echo -e "${GREEN}📊 Database Statistics:${NC}"
    db_size=$(get_db_size)
    echo "Total database size: ${db_size} MB"
    
    # Table loading progress
    echo ""
    echo -e "${YELLOW}📈 Table Loading Progress:${NC}"
    
    # Check each core table
    tables=("MRCONSO" "MRDEF" "MRHIER" "MRREL" "MRSTY" "MRSAT")
    for table in "${tables[@]}"; do
        if table_exists "$table"; then
            count=$(get_table_count "$table")
            if [ "$count" -gt 0 ]; then
                echo -e "✅ $table: ${GREEN}$count records${NC}"
            else
                echo -e "🔄 $table: ${YELLOW}Loading...${NC}"
            fi
        else
            echo -e "⏳ $table: ${YELLOW}Waiting...${NC}"
        fi
    done
    
    echo ""
    
    # Active MySQL processes
    active_queries=$(get_mysql_processes)
    if [ "$active_queries" -gt 0 ]; then
        echo -e "${BLUE}🔄 Active MySQL Processes: $active_queries${NC}"
        
        # Show current loading operations
        loading_info=$(get_loading_info)
        if [ ! -z "$loading_info" ]; then
            echo "Current operations:"
            echo "$loading_info" | head -n 5
        fi
    else
        echo -e "${GREEN}✅ No active loading operations${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}Next update in 30 seconds...${NC}"
    echo "Press Ctrl+C to stop monitoring"
    
    sleep 30
done 