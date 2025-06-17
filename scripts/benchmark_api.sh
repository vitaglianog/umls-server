#!/bin/bash

echo "⚡ UMLS API Performance Benchmark"
echo "================================="
echo "Testing key API endpoints to measure query performance"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# API base URL
API_URL="http://localhost:8000"

# Function to time API calls
time_api_call() {
    local endpoint="$1"
    local description="$2"
    
    echo -e "${BLUE}Testing: $description${NC}"
    echo "Endpoint: $endpoint"
    
    # Make 3 calls and average the time
    local total_time=0
    local success_count=0
    
    for i in {1..3}; do
        start_time=$(date +%s.%N)
        
        response=$(curl -s -w "%{http_code}" "$API_URL$endpoint" -o /dev/null)
        
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        
        if [[ "$response" == "200" ]]; then
            total_time=$(echo "$total_time + $duration" | bc)
            success_count=$((success_count + 1))
            echo "  Call $i: ${duration}s (✅)"
        else
            echo "  Call $i: Failed (HTTP $response) (❌)"
        fi
    done
    
    if [[ $success_count -gt 0 ]]; then
        avg_time=$(echo "scale=3; $total_time / $success_count" | bc)
        echo -e "${GREEN}  Average: ${avg_time}s${NC}"
    else
        echo -e "${YELLOW}  Average: FAILED${NC}"
    fi
    echo ""
}

# Benchmark tests
echo "🔍 Running API Performance Tests..."
echo ""

# Test 1: Term search (most common)
time_api_call "/terms?search=diabetes&ontology=HPO" "Term Search (HPO diabetes)"

# Test 2: CUI search (text heavy)
time_api_call "/cuis?query=heart" "CUI Search (heart)"

# Test 3: CUI info lookup
time_api_call "/cuis/C0001699" "CUI Info Lookup"

# Test 4: Term search with different ontology
time_api_call "/terms?search=cancer&ontology=SNOMEDCT_US" "Term Search (SNOMED cancer)"

# Test 5: CUI search with complex term
time_api_call "/cuis?query=diabetes%20mellitus" "CUI Search (diabetes mellitus)"

echo "📊 Benchmark Summary:"
echo "---------------------"
echo "• Total tests: 5 endpoints"
echo "• Calls per test: 3 (averaged)"
echo "• Focus: Most common API usage patterns"
echo ""
echo "💡 Performance Tips:"
echo "• Times under 0.5s are excellent"
echo "• Times 0.5-2s are good"  
echo "• Times over 2s may benefit from optimization"
echo ""
echo "🚀 To optimize performance:"
echo "./scripts/run_optimization.sh" 