#!/bin/bash

echo "🔍 UMLS API Real-Time Monitor"
echo "============================"
echo "Monitoring API queries, database activity, and performance..."
echo "Press Ctrl+C to stop"
echo ""

# Function to monitor API logs
monitor_api_logs() {
    echo "📡 API Request Logs:"
    echo "-------------------"
    docker-compose logs -f --tail=10 umls-api | while read line; do
        if [[ $line == *"GET /terms"* ]]; then
            timestamp=$(echo "$line" | cut -d' ' -f1-2)
            echo "🔍 [$(date '+%H:%M:%S')] API Search Query: $(echo "$line" | grep -o 'search=[^&]*')"
        elif [[ $line == *"200"* ]]; then
            echo "✅ [$(date '+%H:%M:%S')] Query completed successfully"
        elif [[ $line == *"ERROR"* ]]; then
            echo "❌ [$(date '+%H:%M:%S')] Error: $line"
        fi
    done
}

# Function to show query statistics
show_stats() {
    echo ""
    echo "📊 Quick Stats (last 5 minutes):"
    echo "--------------------------------"
    
    # Count recent API calls
    api_calls=$(docker logs umls-api 2>&1 | tail -100 | grep -c "GET /terms" || echo "0")
    echo "• Recent API calls: $api_calls"
    
    # Check database connections
    db_connections=$(docker exec umls-mysql mysql -u root -pumls_root_password_2024 -e "SHOW PROCESSLIST;" 2>/dev/null | wc -l || echo "N/A")
    echo "• Active DB connections: $db_connections"
    
    # Memory usage
    container_memory=$(docker stats umls-api --no-stream --format "table {{.MemUsage}}" | tail -1)
    echo "• API Memory usage: $container_memory"
    
    echo ""
}

# Run the monitoring
monitor_api_logs &
MONITOR_PID=$!

# Show stats every 30 seconds
while true; do
    sleep 30
    show_stats
done 