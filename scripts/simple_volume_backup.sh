#!/bin/bash

# Simple Docker Volume Backup for UMLS
# Just backs up the critical MySQL data volume

set -e

BACKUP_DIR="$HOME/umls-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
VOLUME_NAME="umls-server_mysql_data"

echo "🗄️  Simple UMLS Volume Backup"
echo "============================="
echo "Backing up volume: $VOLUME_NAME"
echo "Location: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "📦 Creating volume backup (time depends on database size)..."

# Backup just the volume
docker run --rm \
  -v "$VOLUME_NAME":/source:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/umls_volume_${TIMESTAMP}.tar.gz" -C /source .

if [ $? -eq 0 ]; then
    echo "✅ Volume backup completed!"
    echo ""
    echo "📊 Backup details:"
    ls -lh "$BACKUP_DIR/umls_volume_${TIMESTAMP}.tar.gz"
    echo ""
    echo "🔄 To restore this backup:"
    echo "1. Stop containers: docker compose down"
    echo "2. Remove old volume: docker volume rm $VOLUME_NAME"
    echo "3. Create new volume: docker volume create $VOLUME_NAME"
    echo "4. Restore data: docker run --rm -v $VOLUME_NAME:/target -v $BACKUP_DIR:/backup alpine tar xzf /backup/umls_volume_${TIMESTAMP}.tar.gz -C /target"
    echo "5. Start containers: docker compose up -d"
else
    echo "❌ Backup failed!"
    exit 1
fi 