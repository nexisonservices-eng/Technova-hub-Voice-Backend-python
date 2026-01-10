# Docker Deployment Guide

## Quick Start with Docker Desktop

### 1. Prerequisites
- Docker Desktop installed and running
- Groq API key (get free at https://console.groq.com)

### 2. Setup Environment
```bash
# Copy the Docker environment template
cp .env.docker .env

# Edit .env and set your actual Groq API key
# GROQ_API_KEY=your_actual_api_key_here
```

### 3. Build and Run
```bash
# Build and start the service
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 4. Verify Deployment
```bash
# Check service health
curl http://localhost:4000/health

# View logs
docker-compose logs -f

# Check container status
docker-compose ps
```

## Service Endpoints

### REST API
- `http://localhost:4000/` - Health check
- `http://localhost:4000/process-audio` - Audio processing
- `http://localhost:4000/process-text` - Text processing
- `http://localhost:4000/voices` - List TTS voices
- `http://localhost:4000/stats` - Service statistics

### WebSocket
- `ws://localhost:4000/ws/{call_id}` - Real-time voice communication

### Broadcast TTS
- `http://localhost:4000/tts/broadcast` - Batch TTS generation
- `http://localhost:4000/tts/voices` - Available voices

## Docker Commands

### Development
```bash
# Build image
docker-compose build

# Start service
docker-compose up

# Stop service
docker-compose down

# View logs
docker-compose logs -f voice-ai-service
```

### Production
```bash
# Run in production mode
docker-compose -f docker-compose.yml up -d --build

# Scale service (if needed)
docker-compose up -d --scale voice-ai-service=2

# Update service
docker-compose pull && docker-compose up -d
```

### Maintenance
```bash
# Clean up unused images
docker image prune -f

# View resource usage
docker stats

# Access container shell
docker-compose exec voice-ai-service bash
```

## Configuration

### Environment Variables
Key environment variables in `.env`:
- `GROQ_API_KEY` - Required: Your Groq API key
- `DEBUG` - Set to `false` for production
- `LOG_LEVEL` - INFO, WARNING, ERROR
- `CORS_ORIGINS_RAW` - CORS origins (comma-separated)

### Volumes
- `./logs:/app/logs` - Persistent logs
- `./models:/app/models` - Whisper model cache

### Ports
- `4000:4000` - Main API service
- Health check on `/health` endpoint

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using port 4000
   netstat -tulpn | grep :4000
   # Or use different port in docker-compose.yml
   ```

2. **API Key errors**
   ```bash
   # Check environment variables
   docker-compose exec voice-ai-service env | grep GROQ
   ```

3. **Memory issues**
   ```bash
   # Check container resource usage
   docker stats voice-ai-service
   ```

4. **Permission issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER ./logs ./models
   ```

### Logs
```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View specific service logs
docker-compose logs voice-ai-service
```

### Health Checks
```bash
# Manual health check
curl -f http://localhost:4000/health

# Check container health
docker-compose ps
```

## Performance Optimization

### For Production
1. Set `DEBUG=false`
2. Use `LOG_LEVEL=INFO` or `WARNING`
3. Enable Redis caching if needed
4. Monitor resource usage with `docker stats`

### Resource Limits
Add to `docker-compose.yml`:
```yaml
services:
  voice-ai-service:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## Security Notes

- Keep your `.env` file secure and never commit it
- Use strong API keys and rotate them regularly
- Enable authentication in production (`ENABLE_AUTH=true`)
- Configure CORS origins appropriately
- Use HTTPS in production (add reverse proxy)

## Support

For issues:
1. Check container logs: `docker-compose logs`
2. Verify environment variables
3. Check Groq API status
4. Ensure Docker Desktop has sufficient resources
