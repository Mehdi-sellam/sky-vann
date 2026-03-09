#!/bin/bash

# Apply migrations
python manage.py migrate

# Start the Django application
exec "$@"
