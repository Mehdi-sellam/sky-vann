#!/bin/bash

# Configuration
BACKUP_DIR="/home/saad/mysql_backups"
DB_NAME="skyvan"
DB_USER="root"
DB_PASSWORD="rootpassword"
BOT_TOKEN="7922470557:AAEyWam8FXJe9P3cAlmKm9hOyMru_OirIVI"

CHAT_IDS=("1677619773" "1328200470")


# Ensure backup directory exists and set permissions
mkdir -p $BACKUP_DIR
chmod 700 $BACKUP_DIR  # Only the owner can access backups

# Generate a filename with timestamp
BACKUP_FILE="$BACKUP_DIR/backup_$(date +\%F_%H-%M-%S).sql"

# Run MySQL backup inside Docker
docker exec -i $(docker ps -qf "name=db") mysqldump -u$DB_USER -p$DB_PASSWORD $DB_NAME > $BACKUP_FILE

# Verify if the backup was successful
if [ $? -ne 0 ]; then
    ERROR_MSG="🚨 Backup Failed! Database dump failed for $DB_NAME"
    for CHAT_ID in "${CHAT_IDS[@]}"; do
        curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" -d "chat_id=$CHAT_ID&text=$ERROR_MSG"
    done
    echo "Backup failed!"
    exit 1
fi
# Check if the backup file exists and is not empty
if [ ! -s "$BACKUP_FILE" ]; then
    ERROR_MSG="🚨 Backup Failed! Backup file is missing or empty."
    for CHAT_ID in "${CHAT_IDS[@]}"; do
        curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" -d "chat_id=$CHAT_ID&text=$ERROR_MSG"
    done
    echo "Backup file is missing or empty!"
    exit 1
fi

# Set file permissions (only owner can read/write)
chmod 600 $BACKUP_FILE

# Keep only the last 7 backups
find $BACKUP_DIR -type f -mtime +7 -delete

# Send backup to all Telegram users
for CHAT_ID in "${CHAT_IDS[@]}"; do
    echo "Chat ID: $CHAT_ID"
    RESPONSE=$(curl -s -F "chat_id=$CHAT_ID" -F "document=@$BACKUP_FILE" "https://api.telegram.org/bot$BOT_TOKEN/sendDocument")

    # Check if the file was sent successfully
    if [[ $RESPONSE != *'"ok":true'* ]]; then
        ERROR_MSG="🚨 Backup Failed! Could not send the backup to Telegram."
        curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" -d "chat_id=$CHAT_ID&text=$ERROR_MSG"
        echo "Failed to send backup to Telegram for chat ID: $CHAT_ID"
    fi
done

echo "✅ Backup sent to Telegram successfully."
sudo touch /var/log/backup.log /var/log/backup_error.log
sudo chmod 666 /var/log/backup.log /var/log/backup_error.log
CRON_JOB="0 3 * * * /home/saad/sky-manager-api/scripts/backup_mysql.sh >> /var/log/backup.log 2>> /var/log/backup_error.log"
CRON_FILE="/tmp/mycron"

# Check if the cron job already exists
crontab -l | grep -F "$CRON_JOB" || (
    echo "Setting up cron job..."
    crontab -l > $CRON_FILE 2>/dev/null
    echo "$CRON_JOB" >> $CRON_FILE
    crontab $CRON_FILE
    rm $CRON_FILE
)

echo "Cron job verified."
