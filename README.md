# Wake-on-LAN API Service

A containerized REST API service that sends Wake-on-LAN (WOL) magic packets to wake up devices on your network.

## Features

- 🚀 Simple REST API for sending WOL packets
- 🐳 Fully containerized with Docker
- 🔧 Configurable broadcast IP, port, and service port
- 📝 JSON-based request/response
- ❤️ Health check endpoint

## Quick Start

### Using Pre-built Image from GitHub Container Registry

Pull and run the latest image:

```bash
docker run -d --network host -e PORT=5001 --name wol-api-service ghcr.io/bifr0est/wol-api-service:latest
```

Or with docker-compose, update the `docker-compose.yml`:

```yaml
version: '3.8'

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

### Health Check

Check if the service is running:

```bash
curl http://localhost:5001/health
```

Response:
```json
{
  "status": "healthy"
}
```

### Send Wake-on-LAN Packet

Send a POST request with the MAC address of the device you want to wake:

```bash
curl -X POST http://localhost:5001/wake \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "AA:BB:CC:DD:EE:FF"
  }'
```

**Request Body Parameters:**

- `mac_address` (required): MAC address in format `XX:XX:XX:XX:XX:XX` or `XX-XX-XX-XX-XX-XX`
- `broadcast_ip` (optional): Broadcast IP address (default: `255.255.255.255`)
- `port` (optional): UDP port to send the packet to (default: `9`)

**Example with custom broadcast IP:**

```bash
curl -X POST http://localhost:5001/wake \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "broadcast_ip": "192.168.1.255",
    "port": 9
  }'
```

**Success Response:**

```json
{
  "status": "success",
  "message": "Wake-on-LAN packet sent to AA:BB:CC:DD:EE:FF",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "broadcast_ip": "255.255.255.255",
  "port": 9
}
```

**Error Response:**

```json
{
  "error": "mac_address is required"
}
```

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

### Service Port

The API service port can be configured via the `PORT` environment variable (default: 5001).

**In docker-compose.yml:**
```yaml
environment:
  - PORT=8080  # Use any available port
```

**With Docker run:**
```bash
docker run -d --network host -e PORT=8080 --name wol-api-service wol-api-service
```

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
- Verify the JSON format in your request
- Ensure the MAC address format is valid

## License

MIT
