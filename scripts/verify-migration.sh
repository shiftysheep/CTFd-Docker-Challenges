#!/bin/bash
# Verification script for exposed_ports migration

echo "=== Checking Database Schema ==="
docker compose exec -T ctfd mysql -h db -u ctfd -pctfd ctfd -e "DESCRIBE docker_challenge;" 2>/dev/null | grep exposed_ports
if [ $? -eq 0 ]; then
    echo "✓ docker_challenge.exposed_ports column exists"
else
    echo "✗ docker_challenge.exposed_ports column MISSING"
fi

docker compose exec -T ctfd mysql -h db -u ctfd -pctfd ctfd -e "DESCRIBE docker_service_challenge;" 2>/dev/null | grep exposed_ports
if [ $? -eq 0 ]; then
    echo "✓ docker_service_challenge.exposed_ports column exists"
else
    echo "✗ docker_service_challenge.exposed_ports column MISSING"
fi

echo ""
echo "=== Checking Available Docker Images ==="
docker exec ctfd_docker_host docker images --format "{{.Repository}}:{{.Tag}}"

echo ""
echo "=== Checking CTFd API Endpoint ==="
curl -s http://localhost:8000/api/v1/image_ports?image=alpine:latest 2>&1 | head -n 5
