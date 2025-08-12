#!/bin/bash

# RunDown Application Deployment Script
# This script helps you build and deploy the RunDown application using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="rundown"
IMAGE_NAME="rundown:latest"
CONTAINER_NAME="rundown-app"

print_header() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_requirements() {
    print_header "Checking Requirements"
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_warning "Docker Compose is not installed. Some features may not work."
    else
        print_success "Docker Compose is installed"
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it with your configuration."
        echo "Example .env content:"
        echo "CLIENT_SECRET=your-microsoft-client-secret"
        echo "GOOGLE_API_KEY=your-google-api-key"
        exit 1
    fi
    print_success ".env file found"
}

build_image() {
    print_header "Building Docker Image"
    
    echo "Building $IMAGE_NAME..."
    docker build -t $IMAGE_NAME .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

run_container() {
    print_header "Running Container"
    
    # Stop existing container if running
    if docker ps | grep -q $CONTAINER_NAME; then
        echo "Stopping existing container..."
        docker stop $CONTAINER_NAME
    fi
    
    # Remove existing container if exists
    if docker ps -a | grep -q $CONTAINER_NAME; then
        echo "Removing existing container..."
        docker rm $CONTAINER_NAME
    fi
    
    # Create tokens directory if it doesn't exist
    mkdir -p tokens
    mkdir -p logs
    
    # Run new container
    echo "Starting new container..."
    docker run -d \
        --name $CONTAINER_NAME \
        -p 5000:5000 \
        --env-file .env \
        -v $(pwd)/tokens:/app/tokens \
        -v $(pwd)/logs:/app/logs \
        --restart unless-stopped \
        $IMAGE_NAME
    
    if [ $? -eq 0 ]; then
        print_success "Container started successfully"
        echo -e "${GREEN}Application is running at: http://localhost:5000${NC}"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

run_with_compose() {
    print_header "Running with Docker Compose"
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found"
        exit 1
    fi
    
    # Create necessary directories
    mkdir -p tokens logs
    
    # Run with Docker Compose
    docker-compose down
    docker-compose up --build -d
    
    if [ $? -eq 0 ]; then
        print_success "Application started with Docker Compose"
        echo -e "${GREEN}Application is running at: http://localhost:5000${NC}"
    else
        print_error "Failed to start with Docker Compose"
        exit 1
    fi
}

show_logs() {
    print_header "Application Logs"
    docker logs -f $CONTAINER_NAME
}

stop_application() {
    print_header "Stopping Application"
    
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        docker-compose down
        print_success "Docker Compose services stopped"
    else
        if docker ps | grep -q $CONTAINER_NAME; then
            docker stop $CONTAINER_NAME
            docker rm $CONTAINER_NAME
            print_success "Container stopped and removed"
        else
            print_warning "No running container found"
        fi
    fi
}

cleanup() {
    print_header "Cleanup"
    
    # Stop and remove containers
    stop_application
    
    # Remove images
    if docker images | grep -q $APP_NAME; then
        docker rmi $IMAGE_NAME
        print_success "Docker image removed"
    fi
    
    # Remove volumes (optional)
    read -p "Do you want to remove data volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume prune -f
        print_success "Volumes removed"
    fi
}

show_status() {
    print_header "Application Status"
    
    echo "Docker containers:"
    docker ps --filter "name=$CONTAINER_NAME"
    
    echo -e "\nDocker images:"
    docker images | grep $APP_NAME
    
    echo -e "\nApplication health:"
    if docker ps | grep -q $CONTAINER_NAME; then
        curl -f http://localhost:5000/auth/status 2>/dev/null && echo "✅ Application is healthy" || echo "❌ Application is not responding"
    else
        echo "❌ Container is not running"
    fi
}

# Main menu
show_menu() {
    echo -e "${BLUE}RunDown Application Deployment${NC}"
    echo "1) Check requirements"
    echo "2) Build Docker image"
    echo "3) Run container (simple)"
    echo "4) Run with Docker Compose"
    echo "5) Show logs"
    echo "6) Show status"
    echo "7) Stop application"
    echo "8) Cleanup (remove containers and images)"
    echo "9) Exit"
}

# Main execution
case "${1:-menu}" in
    "check")
        check_requirements
        ;;
    "build")
        check_requirements
        build_image
        ;;
    "run")
        check_requirements
        build_image
        run_container
        ;;
    "compose")
        check_requirements
        run_with_compose
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "stop")
        stop_application
        ;;
    "cleanup")
        cleanup
        ;;
    "menu"|*)
        while true; do
            echo
            show_menu
            echo
            read -p "Choose an option (1-9): " choice
            case $choice in
                1) check_requirements ;;
                2) check_requirements && build_image ;;
                3) check_requirements && build_image && run_container ;;
                4) check_requirements && run_with_compose ;;
                5) show_logs ;;
                6) show_status ;;
                7) stop_application ;;
                8) cleanup ;;
                9) echo "Goodbye!"; exit 0 ;;
                *) print_error "Invalid option. Please choose 1-9." ;;
            esac
            echo
            read -p "Press Enter to continue..."
        done
        ;;
esac
