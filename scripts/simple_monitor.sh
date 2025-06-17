#!/bin/bash

echo "🔍 Simple UMLS API Monitor - Real-time logs"
echo "Watch your Claude MCP queries in real-time!"
echo "Press Ctrl+C to stop"
echo ""

# Simple real-time log monitoring with query highlighting
docker-compose logs -f umls-api | grep --line-buffered -E "(GET /terms|POST|Error|Exception)" | while read line; do
    if [[ $line == *"GET /terms"* ]]; then
        echo "🔍 [$(date '+%H:%M:%S')] $(echo "$line" | grep -o 'search=[^&" ]*' | sed 's/search=/Search: /')"
    elif [[ $line == *"ERROR"* ]] || [[ $line == *"Exception"* ]]; then
        echo "❌ [$(date '+%H:%M:%S')] Error detected"
    else
        echo "📡 [$(date '+%H:%M:%S')] API activity"
    fi
done 