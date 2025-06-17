#!/bin/bash

echo "🐳 Docker Resource Monitor"
echo "========================="
echo ""

# Function to show current resource usage
show_resources() {
    echo "📊 Current Resource Usage:"
    echo "--------------------------"
    docker stats umls-api umls-mysql --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    echo ""
    
    # Calculate total usage
    mysql_mem=$(docker stats umls-mysql --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/GiB//' | sed 's/MiB//' | awk '{print $1}')
    api_mem=$(docker stats umls-api --no-stream --format "{{.MemUsage}}" | cut -d'/' -f1 | sed 's/MiB//' | awk '{print $1/1024}')
    
    echo "💾 Memory Summary:"
    echo "• MySQL: ${mysql_mem}GB"
    echo "• API: ${api_mem}GB" 
    echo "• Total Used: ~$(echo "$mysql_mem + $api_mem" | bc)GB"
    echo ""
    
    # System recommendations
    total_docker=$(docker system info 2>/dev/null | grep 'Total Memory' | awk '{print $3}' | sed 's/GiB//')
    echo "🎯 Docker Allocation: ${total_docker}GB"
    
    if (( $(echo "$total_docker > 25" | bc -l) )); then
        echo "⚠️  RECOMMENDATION: Reduce Docker memory to 20-22GB"
    elif (( $(echo "$total_docker < 18" | bc -l) )); then
        echo "⚠️  WARNING: May be too low - consider 20-22GB"
    else
        echo "✅ Good allocation size!"
    fi
    echo ""
}

# Function to monitor continuously
monitor_continuous() {
    echo "🔍 Continuous monitoring (Ctrl+C to stop)..."
    echo ""
    while true; do
        clear
        echo "🐳 Docker Resource Monitor - $(date)"
        echo "=================================="
        show_resources
        sleep 10
    done
}

# Main execution
if [[ "$1" == "--continuous" || "$1" == "-c" ]]; then
    monitor_continuous
else
    show_resources
    echo "💡 For continuous monitoring: $0 --continuous"
fi 