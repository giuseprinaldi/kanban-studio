#!/bin/bash
# Build and start the container in detached mode
docker-compose up --build -d
echo "Kanban Studio is starting up... Navigate to http://localhost:8000"
