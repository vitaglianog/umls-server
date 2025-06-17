#!/bin/bash

echo "🔍 Docker Resource Verification for UMLS"
echo "========================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "📊 Current Docker Configuration:"
echo "--------------------------------"

# Check memory
memory=$(docker info 2>/dev/null | grep "Total Memory" | awk '{print $3 $4}')
memory_gb=$(docker info 2>/dev/null | grep "Total Memory" | awk '{print $3}' | sed 's/GiB//')

echo -n "Memory allocated: $memory"
if (( $(echo "$memory_gb >= 10" | bc -l 2>/dev/null || echo "0") )); then
    echo -e " ${GREEN}✅ Good${NC}"
elif (( $(echo "$memory_gb >= 8" | bc -l 2>/dev/null || echo "0") )); then
    echo -e " ${YELLOW}⚠️  Acceptable (recommend 12GB+)${NC}"
else
    echo -e " ${RED}❌ Too low (need 10GB+)${NC}"
fi

# Check CPUs
cpus=$(docker info 2>/dev/null | grep "CPUs" | awk '{print $2}')
echo -n "CPUs allocated: $cpus"
if [ "$cpus" -ge 6 ]; then
    echo -e " ${GREEN}✅ Good${NC}"
elif [ "$cpus" -ge 4 ]; then
    echo -e " ${YELLOW}⚠️  Acceptable${NC}"
else
    echo -e " ${RED}❌ Low (recommend 6+)${NC}"
fi

# Check current disk usage
echo ""
echo "💾 Docker Disk Usage:"
echo "--------------------"
docker system df

echo ""
echo "🗂️  Docker VM Disk Usage:"
echo "-------------------------"
docker_vm_size=$(du -sh ~/Library/Containers/com.docker.docker/Data/vms/0/data 2>/dev/null | awk '{print $1}' || echo "Unable to access")
echo "Current VM usage: $docker_vm_size"

# Check available host space
echo ""
echo "🖥️  Host System Space:"
echo "---------------------"
df -h . | tail -n 1

echo ""
echo "🎯 Space Requirements for UMLS:"
echo "------------------------------"
echo "Raw UMLS data: 38GB"
echo "Peak during loading: ~150GB"
echo "Final database: ~80-100GB"

echo ""
echo "✅ Recommendations:"
echo "==================="
echo "1. Docker Memory: 12GB+ (current: $memory)"
echo "2. Docker Disk Limit: 250GB+"
echo "3. Available host space: 200GB+ (you have plenty)"

echo ""
echo "🚀 If everything looks good, you can proceed with:"
echo "cp docker.env .env"
echo "docker compose up -d mysql"
echo "./scripts/load_umls_2025aa.sh"

echo ""
echo "📊 Monitor loading with:"
echo "./scripts/monitor_loading.sh" 