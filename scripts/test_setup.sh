#!/bin/bash

# Test script to verify UMLS Docker setup

set -e

echo "🧪 Testing UMLS Docker Setup"
echo "============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_docker_compose() {
    echo -n "🐳 Checking Docker Compose... "
    if command -v docker compose &> /dev/null; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "   Docker Compose not found. Please install Docker Desktop."
        return 1
    fi
}

test_containers_running() {
    echo -n "📦 Checking containers... "
    
    # Check if MySQL container is running
    if docker compose ps | grep -q "umls-mysql.*running"; then
        echo -e "${GREEN}MySQL running${NC}"
        mysql_running=true
    else
        echo -e "${YELLOW}MySQL not running${NC}"
        mysql_running=false
    fi
    
    # Check if API container is running
    if docker compose ps | grep -q "umls-api.*running"; then
        echo "   API container: ${GREEN}running${NC}"
        api_running=true
    else
        echo "   API container: ${YELLOW}not running${NC}"
        api_running=false
    fi
    
    return 0
}

test_mysql_connection() {
    echo -n "🗄️  Testing MySQL connection... "
    
    if ! $mysql_running; then
        echo -e "${YELLOW}SKIPPED (MySQL not running)${NC}"
        return 0
    fi
    
    if docker exec umls-mysql mysql -u umls_user -pumls_password_secure_2024 -e "SELECT 1" umls &>/dev/null; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "   Cannot connect to MySQL database"
        return 1
    fi
}

test_api_health() {
    echo -n "🔗 Testing API health... "
    
    if ! $api_running; then
        echo -e "${YELLOW}SKIPPED (API not running)${NC}"
        return 0
    fi
    
    # Wait a moment for API to be ready
    sleep 2
    
    if curl -s http://localhost:8000/terms?search=test 2>/dev/null | grep -q "results\|No results found"; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo "   API not responding or returning unexpected format"
        return 1
    fi
}

test_umls_tables() {
    echo -n "📊 Checking UMLS tables... "
    
    if ! $mysql_running; then
        echo -e "${YELLOW}SKIPPED (MySQL not running)${NC}"
        return 0
    fi
    
    # Check if main UMLS tables exist
    tables=$(docker exec umls-mysql mysql -u umls_user -pumls_password_secure_2024 umls -e "SHOW TABLES" 2>/dev/null | grep -E "(MRCONSO|MRDEF|MRHIER|MRREL)" | wc -l)
    
    if [ "$tables" -eq 4 ]; then
        echo -e "${GREEN}All 4 tables exist${NC}"
        
        # Check if tables have data
        echo -n "📈 Checking table data... "
        data_count=$(docker exec umls-mysql mysql -u umls_user -pumls_password_secure_2024 umls -e "SELECT (SELECT COUNT(*) FROM MRCONSO) + (SELECT COUNT(*) FROM MRDEF) + (SELECT COUNT(*) FROM MRHIER) + (SELECT COUNT(*) FROM MRREL) as total" 2>/dev/null | tail -n 1)
        
        if [ "$data_count" -gt 0 ]; then
            echo -e "${GREEN}Data found ($data_count total records)${NC}"
        else
            echo -e "${YELLOW}No data found (tables are empty)${NC}"
        fi
        
        return 0
    elif [ "$tables" -gt 0 ]; then
        echo -e "${YELLOW}Only $tables/4 tables exist${NC}"
        return 0
    else
        echo -e "${YELLOW}No UMLS tables found${NC}"
        return 0
    fi
}

show_status() {
    echo ""
    echo "📋 Current Status:"
    echo "=================="
    
    echo -n "Docker Compose: "
    if command -v docker compose &> /dev/null; then
        echo -e "${GREEN}Installed${NC}"
    else
        echo -e "${RED}Not installed${NC}"
    fi
    
    echo -n "MySQL Container: "
    if docker compose ps | grep -q "umls-mysql.*running"; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Not running${NC}"
    fi
    
    echo -n "API Container: "
    if docker compose ps | grep -q "umls-api.*running"; then
        echo -e "${GREEN}Running${NC}"
    else
        echo -e "${RED}Not running${NC}"
    fi
    
    echo -n "Environment file: "
    if [ -f ".env" ]; then
        echo -e "${GREEN}Present${NC}"
    else
        echo -e "${YELLOW}Missing (copy docker.env to .env)${NC}"
    fi
    
    echo -n "UMLS data directory: "
    if [ -d "umls-data" ]; then
        # Check for 2025AA structure first
        if [ -d "umls-data/2025AA/META" ]; then
            file_count=$(ls -1 umls-data/2025AA/META/*.RRF 2>/dev/null | wc -l)
            echo -e "${GREEN}Present with UMLS 2025AA ($file_count .RRF files)${NC}"
        else
            # Check for files in root umls-data
            file_count=$(ls -1 umls-data/*.RRF 2>/dev/null | wc -l)
            if [ "$file_count" -gt 0 ]; then
                echo -e "${GREEN}Present with $file_count .RRF files${NC}"
            else
                echo -e "${YELLOW}Present but no .RRF files${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}Missing${NC}"
    fi
}

provide_next_steps() {
    echo ""
    echo "🎯 Next Steps:"
    echo "=============="
    
    if ! command -v docker compose &> /dev/null; then
        echo "1. Install Docker Desktop"
    fi
    
    if [ ! -f ".env" ]; then
        echo "2. Copy environment file: cp docker.env .env"
    fi
    
    if ! docker compose ps | grep -q "umls-mysql.*running"; then
        echo "3. Start MySQL: docker compose up -d mysql"
    fi
    
    # Check if UMLS data needs to be loaded
    if [ -d "umls-data/2025AA/META" ]; then
        if [ $(ls -1 umls-data/2025AA/META/*.RRF 2>/dev/null | wc -l) -gt 0 ]; then
            echo "4. Load UMLS 2025AA data: ./scripts/load_umls_2025aa.sh"
        else
            echo "4. UMLS 2025AA directory found but no .RRF files"
        fi
    elif [ ! -d "umls-data" ] || [ $(ls -1 umls-data/*.RRF 2>/dev/null | wc -l) -eq 0 ]; then
        echo "4. Download UMLS data and place .RRF files in umls-data/"
        echo "5. Load data: ./scripts/load_umls_data.sh"
    fi
    
    if ! docker compose ps | grep -q "umls-api.*running"; then
        echo "6. Start API: docker compose up -d umls-api"
    fi
    
    echo "7. Test API: curl 'http://localhost:8000/terms?search=diabetes&ontology=HPO'"
}

# Main execution
echo ""

# Run tests
test_docker_compose
test_containers_running
test_mysql_connection
test_api_health
test_umls_tables

# Show current status
show_status

# Provide guidance
provide_next_steps

echo ""
echo -e "${GREEN}🎉 Test completed!${NC}"
echo ""
echo "For detailed setup instructions, see: DOCKER_SETUP.md" 