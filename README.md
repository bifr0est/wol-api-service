# Wake-on-LAN API Service

A simple containerized HTTP service that sends Wake-on-LAN (WOL) magic packets to wake up devices on your network.

## Features

- 🚀 Simple HTTP API for sending WOL packets
- 🐳 Fully containerized with Docker
- 🔧 Configurable broadcast IP, UDP port, and service port
- 🌐 Web interface included
- ❤️ Health check endpoint
- 📦 Zero external dependencies - pure Python stdlib
- 🔒 Optional API key authentication
- 🌍 Optional CORS support for web frontends
- ⚡ Built-in rate limiting to prevent abuse
- 🐍 Python 3.13 with full type hints

## Quick Start

### Using Pre-built Image from GitHub Container Registry

Pull and run the latest image:

```bash
docker run -d --network host -e PORT=5001 --name wol-api-service ghcr.io/bifr0est/wol-api-service:latest
```

Or with docker-compose, update the `docker-compose.yml`:

```yaml
services:
  wol-api:
    image: ghcr.io/bifr0est/wol-api-service:latest
    container_name: wol-api-service
    network_mode: "host"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
      - PORT=5001
```

Then run:
```bash
docker-compose up -d
```

### Building from Source

#### Using Docker Compose (Recommended)

1. Build and start the container:
```bash
docker-compose up -d --build
```

2. Check if the service is running:
```bash
curl http://localhost:5001/health
```

You can also open http://localhost:5001 in your browser to use the web interface.

> **Note:** The default service port is 5001. You can change it by setting the `PORT` environment variable in `docker-compose.yml`.

#### Using Docker

1. Build the image:
```bash
docker build -t wol-api-service .
```

2. Run the container:
```bash
docker run -d --network host -e PORT=5001 --name wol-api-service wol-api-service
```

> **Note:** The `--network host` flag is required for the container to send broadcast packets on your local network. When using host networking, the `-p` port mapping flag is not needed.

## API Usage

### Web Interface

Open http://localhost:5001 in your browser to access the simple web form where you can enter:
- MAC address
- Broadcast IP (optional)
- UDP port (optional)

### Health Check

Check if the service is running:

```bash
curl http://localhost:5001/health
```

Response:
```
OK
```

### Send Wake-on-LAN Packet via URL

Send a simple GET request with the MAC address as a URL parameter:

```bash
curl "http://localhost:5001/wake?mac=AA:BB:CC:DD:EE:FF"
```

**URL Parameters:**

- `mac` (required): MAC address in format `XX:XX:XX:XX:XX:XX` or `XX-XX-XX-XX-XX-XX`
- `broadcast` (optional): Broadcast IP address (default: `255.255.255.255`)
- `port` (optional): UDP port to send the WOL packet to (default: `9`)

**Example with custom broadcast IP and port:**

```bash
curl "http://localhost:5001/wake?mac=AA:BB:CC:DD:EE:FF&broadcast=192.168.1.255&port=7"
```

**Success Response:**

```
OK - WOL packet sent to AA:BB:CC:DD:EE:FF
```

**Error Response:**

```
400 Bad Request - Missing 'mac' parameter
```

### Important: Understanding the Ports

- **Service Port** (default: 5001): The HTTP port where this service runs
- **UDP Port** (default: 9): The destination port for the WOL magic packet
  - Port 9 is most common (discard protocol)
  - Port 7 is also widely used (echo protocol)
  - Some devices may require different ports

## Requirements for Wake-on-LAN to Work

For the target device to wake up, it must:

1. Support Wake-on-LAN (check BIOS/UEFI settings)
2. Have Wake-on-LAN enabled in the operating system's network adapter settings
3. Be connected via Ethernet (WOL typically doesn't work over Wi-Fi)
4. Be in sleep/hibernate mode (not completely powered off, unless BIOS supports it)

## Container Management

**Stop the service:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f
```

**Restart the service:**
```bash
docker-compose restart
```

## Configuration

### Environment Variables

The service can be configured using the following environment variables:

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PORT` | HTTP service port | `5001` | `8080` |
| `API_KEY` | Optional API key for authentication | (none) | `your-secret-key-123` |
| `ENABLE_CORS` | Enable CORS headers for web frontends | `false` | `true` |
| `RATE_LIMIT_REQUESTS` | Max requests per time window | `10` | `20` |
| `RATE_LIMIT_WINDOW` | Rate limit time window in seconds | `60` | `120` |

### Service Port

The API service port can be configured via the `PORT` environment variable (default: 5001).

**In docker-compose.yml:**
```yaml
environment:
  - PORT=8080  # Use any available port
  - API_KEY=my-secret-key-123  # Enable authentication
  - ENABLE_CORS=true  # Enable CORS
  - RATE_LIMIT_REQUESTS=20  # Allow 20 requests
  - RATE_LIMIT_WINDOW=60  # Per 60 seconds
```

**With Docker run:**
```bash
docker run -d --network host \
  -e PORT=8080 \
  -e API_KEY=my-secret-key-123 \
  -e ENABLE_CORS=true \
  --name wol-api-service wol-api-service
```

### Authentication

When `API_KEY` is set, the service requires authentication for all `/wake` requests (but not `/health`).

**Option 1: Authorization header (recommended)**
```bash
curl -H "Authorization: Bearer your-secret-key-123" \
  "http://localhost:5001/wake?mac=AA:BB:CC:DD:EE:FF"
```

**Option 2: Query parameter**
```bash
curl "http://localhost:5001/wake?mac=AA:BB:CC:DD:EE:FF&api_key=your-secret-key-123"
```

### Rate Limiting

Rate limiting is enabled by default to prevent abuse:
- Default: 10 requests per 60 seconds per IP address
- Configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`
- Returns `429 Too Many Requests` when exceeded

### CORS Support

Enable CORS for cross-origin requests from web frontends:
```yaml
environment:
  - ENABLE_CORS=true
```

This allows JavaScript applications on different domains to call the API.

### Network Configuration

The container uses `network_mode: host` to access the host's network directly, which is necessary for broadcasting WOL packets. This means:

- The service will be accessible on the host's IP at the configured port (default: 5001)
- The container can send broadcast packets on the local network
- Port mapping (`-p` flag) is not used with host networking

If you need to use a specific broadcast address for a subnet, include it in your API requests.

## Troubleshooting

**Container can't send broadcast packets:**
- Ensure you're using `--network host` or `network_mode: host`
- Check firewall settings on the host machine

**Target device doesn't wake up:**
- Verify Wake-on-LAN is enabled in the device's BIOS and OS settings
- Ensure the device is on the same network or accessible via the broadcast address
- Try using the subnet-specific broadcast address (e.g., `192.168.1.255` instead of `255.255.255.255`)
- Check that the MAC address is correct

**API returns errors:**
- Check the logs: `docker-compose logs -f`
- Verify the MAC address format is valid
- If authentication is enabled, ensure API key is correct
- Check if rate limit is exceeded (wait or adjust limits)

**CORS errors in browser:**
- Set `ENABLE_CORS=true` in environment variables
- Restart the container after configuration changes

## License

MIT
