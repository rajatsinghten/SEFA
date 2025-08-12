# RunDown - Container Deployment Guide

## Overview
This guide provides multiple deployment options for the RunDown application using Docker containers. Choose the option that best fits your deployment needs.

## 🚀 Quick Start

### Prerequisites
- Docker installed on your system
- Docker Compose (optional, for advanced deployments)
- Your `.env` file configured with proper credentials

### Fastest Deployment
```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the interactive deployment menu
./deploy.sh

# Or run directly with Docker Compose
./deploy.sh compose
```

## 📦 Deployment Options

### 1. Simple Docker Container
```bash
# Build the image
docker build -t rundown:latest .

# Run the container
docker run -d \
  --name rundown-app \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/tokens:/app/tokens \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  rundown:latest
```

### 2. Docker Compose (Recommended)
```bash
# Start the application with all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The Docker Compose setup includes:
- **RunDown App**: Main application container
- **Redis**: Session storage (optional scaling)
- **Nginx**: Reverse proxy with rate limiting

### 3. Kubernetes Deployment
```bash
# Apply the Kubernetes configuration
kubectl apply -f kubernetes.yaml

# Check deployment status
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/rundown-app
```

## 🔧 Configuration Files

### Dockerfile
- Uses Python 3.11 slim base image
- Installs dependencies and copies application code
- Runs as non-root user for security
- Includes health checks
- Exposes port 5000

### docker-compose.yml
- **rundown-app**: Main application service
- **redis**: Optional Redis for session storage
- **nginx**: Optional Nginx reverse proxy
- Includes health checks and restart policies
- Persistent volumes for tokens and logs

### kubernetes.yaml
Complete Kubernetes configuration with:
- **Deployment**: Application pods with resource limits
- **Service**: LoadBalancer for external access
- **Secrets**: Secure credential storage
- **PersistentVolumeClaims**: Data persistence
- **Ingress**: Domain-based routing with SSL

### nginx.conf
- Reverse proxy configuration
- Rate limiting (10 requests/second)
- Security headers
- Static file serving
- SSL configuration template

## 🔐 Environment Variables

Required environment variables in your `.env` file:

```env
# Microsoft Graph API
CLIENT_SECRET=your-microsoft-client-secret
CLIENT_ID=4b7b4c3c-60f0-4f92-bd1d-c222f7683a64
TENANT_ID=c68bfe4b-5da1-432f-a631-69a9f35b5f4b

# Google AI
GOOGLE_API_KEY=your-google-api-key

# Flask Configuration
FLASK_ENV=production
PORT=5000

# Optional: Redis (if using)
REDIS_URL=redis://redis:6379/0
```

## 🔍 Health Checks

All deployment options include health checks:
- **Endpoint**: `/auth/status`
- **Interval**: Every 30 seconds
- **Timeout**: 30 seconds
- **Retries**: 3 attempts

## 📊 Resource Requirements

### Minimum Requirements
- **CPU**: 250m (0.25 cores)
- **Memory**: 256Mi
- **Storage**: 1Gi for tokens, 2Gi for logs

### Recommended for Production
- **CPU**: 500m (0.5 cores)
- **Memory**: 512Mi
- **Storage**: 5Gi for tokens, 10Gi for logs

## 🌐 Production Considerations

### SSL/HTTPS Setup
1. Obtain SSL certificates
2. Update nginx configuration
3. Configure domain routing
4. Update redirect URIs in Azure portal

### Scaling
- Use multiple replicas in Kubernetes
- Implement Redis for session sharing
- Configure load balancer properly
- Monitor resource usage

### Security
- Use secrets management (Kubernetes secrets, Docker secrets)
- Implement network policies
- Regular security updates
- Monitor access logs

## 🔧 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 5000
   lsof -i :5000
   
   # Kill the process or change port
   docker run -p 8080:5000 ...
   ```

2. **Permission Errors**
   ```bash
   # Ensure proper ownership of volumes
   sudo chown -R $(id -u):$(id -g) tokens logs
   ```

3. **Container Won't Start**
   ```bash
   # Check logs
   docker logs rundown-app
   
   # Check environment variables
   docker exec rundown-app env
   ```

4. **Health Check Failures**
   ```bash
   # Test health endpoint manually
   curl http://localhost:5000/auth/status
   
   # Check application logs
   docker logs rundown-app
   ```

### Debugging Commands

```bash
# Access container shell
docker exec -it rundown-app /bin/bash

# View all container processes
docker ps -a

# Check container resource usage
docker stats

# View detailed container information
docker inspect rundown-app

# Check Docker Compose services
docker-compose ps
docker-compose logs service-name
```

## 📈 Monitoring

### Application Metrics
- Health check endpoint: `/auth/status`
- Authentication success rates
- API response times
- Error rates and types

### Infrastructure Metrics
- Container CPU and memory usage
- Network traffic and latency
- Storage utilization
- Container restart counts

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
./deploy.sh compose

# Or manually with Docker Compose
docker-compose down
docker-compose up --build -d
```

### Backup Strategy
```bash
# Backup tokens and configuration
tar -czf backup-$(date +%Y%m%d).tar.gz tokens/ .env

# For Kubernetes
kubectl get secret rundown-secrets -o yaml > secrets-backup.yaml
```

## 🎯 Deployment Script Usage

The `deploy.sh` script provides an interactive menu:

```bash
./deploy.sh                 # Interactive menu
./deploy.sh check          # Check requirements
./deploy.sh build          # Build Docker image
./deploy.sh run            # Run simple container
./deploy.sh compose        # Run with Docker Compose
./deploy.sh logs           # View logs
./deploy.sh status         # Check status
./deploy.sh stop           # Stop application
./deploy.sh cleanup        # Remove containers and images
```

This comprehensive setup provides flexibility for development, testing, and production deployments while maintaining security and scalability best practices.
