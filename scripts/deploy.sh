#!/bin/bash

# Usage: ./deploy.sh <service_name> <build_type> <deploy_path> <restart_command>

SERVICE_NAME=$1
BUILD_TYPE=$2
DEPLOY_PATH=$3
RESTART_COMMAND=$4

WINDOWS_USER="user"
WINDOWS_HOST="windows-server"

echo "Deploying service: $SERVICE_NAME"
echo "Build type: $BUILD_TYPE"
echo "Deploy path: $DEPLOY_PATH"
echo "Restart command: $RESTART_COMMAND"

ssh ${WINDOWS_USER}@${WINDOWS_HOST} <<EOF
cd "$DEPLOY_PATH"
if [ "$BUILD_TYPE" = "docker" ]; then
    docker-compose build
    docker-compose up -d
    $RESTART_COMMAND
elif [ "$BUILD_TYPE" = "python" ]; then
    pip install -r requirements.txt
    $RESTART_COMMAND
elif [ "$BUILD_TYPE" = "python_script" ]; then
    $RESTART_COMMAND
else
    echo "Unknown build type: $BUILD_TYPE"
fi
EOF

