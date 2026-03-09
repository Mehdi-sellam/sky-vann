#!/bin/bash

cd  /root/sky-manager-api/skyvan/
echo "Running docker-compose up"
docker-compose up -d
echo "______ migrate______"

# Wait for the containers to be fully up and running
sleep 90

# Run migrations and capture the output
docker-compose  run web python manage.py migrate

# Capture the exit status of the migrate command
MIGRATE_EXIT_STATUS=$?

# Display the output and exit status of the migrate command
if [ $MIGRATE_EXIT_STATUS -ne 0 ]; then
    echo "Migrations failed with exit status $MIGRATE_EXIT_STATUS"
    exit $MIGRATE_EXIT_STATUS
else
    echo "Migrations completed successfully"
fi
