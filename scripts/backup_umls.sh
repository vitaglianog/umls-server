#!/bin/bash

# UMLS Complete Backup Script
# Creates a snapshot of the entire UMLS system for rollback

set -e

BACKUP_DIR="$HOME/umls-backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="umls_snapshot_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🗄️  UMLS Complete Backup Script${NC}"
echo "=================================="
echo "Creating snapshot: $BACKUP_NAME"
echo "Location: $BACKUP_PATH"
echo ""

# Create backup directory
mkdir -p "$BACKUP_PATH"

echo -e "${BLUE}📦 Step 1: Backing up Docker Volume (MySQL Data)...${NC}"
echo "This is the most critical part - your UMLS database"

# Method 1: Volume backup using docker run
echo "Creating volume backup..."
docker run --rm \
  -v umls-server_mysql_data:/source:ro \
  -v "$BACKUP_PATH":/backup \
  alpine tar czf /backup/mysql_data_volume.tar.gz -C /source .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Volume backup completed${NC}"
    # Show size
    ls -lh "$BACKUP_PATH/mysql_data_volume.tar.gz"
else
    echo "❌ Volume backup failed"
    exit 1
fi

echo ""
echo -e "${BLUE}📋 Step 2: Backing up Application Code...${NC}"

# Backup application directory (excluding node_modules, logs, etc.)
tar czf "$BACKUP_PATH/umls_application.tar.gz" \
  --exclude='*.log' \
  --exclude='logs/*' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='umls-data' \
  --exclude='node_modules' \
  -C .. "$(basename "$PWD")"

echo -e "${GREEN}✅ Application backup completed${NC}"
ls -lh "$BACKUP_PATH/umls_application.tar.gz"

echo ""
echo -e "${BLUE}🐳 Step 3: Saving Docker Configuration...${NC}"

# Save Docker Compose configuration
cp docker-compose.yml "$BACKUP_PATH/"
cp docker.env "$BACKUP_PATH/" 2>/dev/null || echo "docker.env not found (optional)"

# Save current container states
docker compose ps > "$BACKUP_PATH/docker_status.txt"
docker images | grep -E "(mysql|umls)" > "$BACKUP_PATH/docker_images.txt"

echo -e "${GREEN}✅ Docker configuration saved${NC}"

echo ""
echo -e "${BLUE}📊 Step 4: Database Metadata...${NC}"

# Save database schema and stats (quick backup)
docker exec umls-mysql mysqldump \
  -u umls_user -pumls_password_secure_2024 \
  --no-data --routines --triggers umls > "$BACKUP_PATH/schema_only.sql"

docker exec umls-mysql mysql -u umls_user -pumls_password_secure_2024 umls -e "
SELECT TABLE_NAME, TABLE_ROWS, 
       ROUND((DATA_LENGTH + INDEX_LENGTH)/1024/1024/1024, 2) as 'Size_GB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'umls' 
ORDER BY TABLE_ROWS DESC;" > "$BACKUP_PATH/table_stats.txt"

echo -e "${GREEN}✅ Database metadata saved${NC}"

echo ""
echo -e "${BLUE}📝 Step 5: Creating restore instructions...${NC}"

cat > "$BACKUP_PATH/RESTORE_INSTRUCTIONS.md" << 'EOF'
# UMLS Restore Instructions

## Prerequisites
- Docker and Docker Compose installed
- Sufficient disk space (40GB+)

## Restore Steps

### 1. Stop current containers (if any)
```bash
docker compose down
docker volume rm umls-server_mysql_data 2>/dev/null || true
```

### 2. Restore application code
```bash
cd /path/to/restore/location
tar xzf umls_application.tar.gz
cd umls-server
```

### 3. Restore Docker volume
```bash
# Create new volume
docker volume create umls-server_mysql_data

# Restore data
docker run --rm \
  -v umls-server_mysql_data:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/mysql_data_volume.tar.gz -C /target
```

### 4. Start services
```bash
cp docker.env .env  # Edit if needed
docker compose up -d
```

### 5. Verify restoration
```bash
# Wait for MySQL to start
sleep 30

# Test database
docker exec umls-mysql mysql -u umls_user -pumls_password_secure_2024 umls \
  -e "SELECT COUNT(*) FROM MRCONSO;"

# Should return: 17144356
```

## Files in this backup:
- `mysql_data_volume.tar.gz` - Complete MySQL database
- `umls_application.tar.gz` - Application code and scripts  
- `docker-compose.yml` - Container configuration
- `schema_only.sql` - Database schema backup
- `table_stats.txt` - Database statistics
- `docker_status.txt` - Container status when backed up
EOF

echo -e "${GREEN}✅ Restore instructions created${NC}"

echo ""
echo -e "${BLUE}📊 Backup Summary:${NC}"
echo "=================="
du -sh "$BACKUP_PATH"/*
echo ""
echo "Total backup size:"
du -sh "$BACKUP_PATH"

echo ""
echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📍 Backup location:${NC} $BACKUP_PATH"
echo -e "${YELLOW}🔄 To restore:${NC} Follow instructions in RESTORE_INSTRUCTIONS.md"
echo ""

# Create quick restore script
cat > "$BACKUP_PATH/quick_restore.sh" << EOF
#!/bin/bash
# Quick restore script for this backup

BACKUP_DIR="\$(dirname "\$0")"
echo "Restoring UMLS from: \$BACKUP_DIR"

# Stop containers
docker compose down 2>/dev/null || true

# Remove old volume
docker volume rm umls-server_mysql_data 2>/dev/null || true

# Create new volume
docker volume create umls-server_mysql_data

# Restore volume data
echo "Restoring MySQL data (this may take several minutes)..."
docker run --rm \\
  -v umls-server_mysql_data:/target \\
  -v "\$BACKUP_DIR":/backup \\
  alpine tar xzf /backup/mysql_data_volume.tar.gz -C /target

echo "✅ Volume restored"

echo "Copy docker-compose.yml and start containers manually:"
echo "cp \$BACKUP_DIR/docker-compose.yml ."
echo "cp \$BACKUP_DIR/docker.env .env"
echo "docker compose up -d"
EOF

chmod +x "$BACKUP_PATH/quick_restore.sh"

echo -e "${GREEN}🚀 Quick restore script created: $BACKUP_PATH/quick_restore.sh${NC}" 