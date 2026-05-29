# Deployment

How to run your Zinq agent in production. Covers everything from local development to cloud deployment.

## Overview

Your agent is just a Python script. How you deploy it depends on your pattern:

| Pattern | What You Need | Best For |
|---------|---------------|----------|
| **Polling agent** (no webhooks) | A machine that runs Python | Cron jobs, periodic checks |
| **Webhook agent** | A publicly reachable HTTP server | Real-time responses |

## Local Development

The simplest setup. Good for building and testing.

### Polling agent (no webhook)

Just run your script:

```bash
export ZINQ_API_KEY=zak_your_key
python my_agent.py
```

### Webhook agent

You need a tunnel to make your local machine reachable by Zinq's servers.

```bash
# Terminal 1: Start your agent
export ZINQ_API_KEY=zak_your_key
# ZINQ_WEBHOOK_SECRET — not yet available, use skip_signature_check=True
python my_agent.py

# Terminal 2: Start a tunnel
ngrok http 8080
# Copy the https URL and set it as your webhook URL in the Zinq app
```

For development, you can skip signature verification:

```python
webhook = ZinqWebhook(secret="dev", skip_signature_check=True)
```

---

## macOS launchd

Auto-start your agent when you log in on macOS.

### Step 1: Create the plist file

```bash
mkdir -p ~/Library/LaunchAgents
```

Create `~/Library/LaunchAgents/com.zinq.my-agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zinq.my-agent</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/you/agents/my_agent.py</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ZINQ_API_KEY</key>
        <string>zak_your_key</string>
        <key>ZINQ_WEBHOOK_SECRET</key>
        <!-- ZINQ_WEBHOOK_SECRET not yet available, use skip_signature_check=True -->
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/zinq-agent.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/zinq-agent.err</string>
</dict>
</plist>
```

### Step 2: Load and start

```bash
launchctl load ~/Library/LaunchAgents/com.zinq.my-agent.plist

# Check status
launchctl list | grep zinq

# View logs
tail -f /tmp/zinq-agent.log

# Stop
launchctl unload ~/Library/LaunchAgents/com.zinq.my-agent.plist
```

---

## Linux systemd

Run your agent as a system service on any Linux server.

### Step 1: Create a virtual environment

```bash
mkdir -p /opt/zinq-agent
cd /opt/zinq-agent
python3 -m venv venv
source venv/bin/activate
pip install zinq-agent[webhook]

# Copy your agent script
cp /path/to/my_agent.py /opt/zinq-agent/
```

### Step 2: Create the environment file

```bash
sudo tee /opt/zinq-agent/.env << 'EOF'
ZINQ_API_KEY=zak_your_key
# ZINQ_WEBHOOK_SECRET — not yet available
EOF

sudo chmod 600 /opt/zinq-agent/.env
```

### Step 3: Create the service file

```bash
sudo tee /etc/systemd/system/zinq-agent.service << 'EOF'
[Unit]
Description=Zinq Agent
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/zinq-agent
EnvironmentFile=/opt/zinq-agent/.env
ExecStart=/opt/zinq-agent/venv/bin/python my_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Step 4: Start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable zinq-agent
sudo systemctl start zinq-agent

# Check status
sudo systemctl status zinq-agent

# View logs
sudo journalctl -u zinq-agent -f

# Restart after code changes
sudo systemctl restart zinq-agent
```

---

## Docker

Containerize your agent for consistent deployments anywhere.

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY my_agent.py .

# Expose webhook port
EXPOSE 8080

CMD ["python", "my_agent.py"]
```

### requirements.txt

```
zinq-agent[webhook]>=0.1.0
```

### Build and run

```bash
# Build
docker build -t my-zinq-agent .

# Run
docker run -d \
  --name zinq-agent \
  -p 8080:8080 \
  -e ZINQ_API_KEY=zak_your_key \
  -e # ZINQ_WEBHOOK_SECRET — not yet available \
  --restart unless-stopped \
  my-zinq-agent

# View logs
docker logs -f zinq-agent

# Stop
docker stop zinq-agent
```

### docker-compose.yml

```yaml
version: "3.8"
services:
  zinq-agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - ZINQ_API_KEY=zak_your_key
      - # ZINQ_WEBHOOK_SECRET — not yet available
    restart: unless-stopped
```

```bash
docker compose up -d
docker compose logs -f
```

---

## Google Cloud (Compute Engine)

Run on GCP's always-free tier (e2-micro instance).

### Step 1: Create a VM

```bash
gcloud compute instances create zinq-agent \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --tags=http-server

# Allow inbound HTTP for webhooks
gcloud compute firewall-rules create allow-zinq-webhook \
  --allow=tcp:8080 \
  --target-tags=http-server
```

### Step 2: SSH in and set up

```bash
gcloud compute ssh zinq-agent

# Install Python and pip
sudo apt update && sudo apt install -y python3-pip python3-venv

# Set up agent
mkdir -p /opt/zinq-agent && cd /opt/zinq-agent
python3 -m venv venv
source venv/bin/activate
pip install zinq-agent[webhook]

# Copy your agent script (or use scp/git)
nano my_agent.py
```

### Step 3: Set up systemd (see [Linux systemd section](#linux-systemd) above)

### Step 4: Set your webhook URL

Your webhook URL is: `http://EXTERNAL_IP:8080/webhook`

Find your external IP:
```bash
gcloud compute instances describe zinq-agent --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

---

## AWS (EC2)

Run on AWS's free tier (t2.micro or t3.micro).

### Step 1: Launch an instance

- Go to EC2 console and click "Launch Instance"
- Choose Amazon Linux 2023 or Ubuntu 22.04
- Instance type: t2.micro (free tier eligible)
- Create a security group allowing TCP 8080 inbound
- Launch and note the public IP

### Step 2: SSH in and set up

```bash
ssh -i your-key.pem ec2-user@YOUR_IP

# Install Python
sudo yum install python3-pip  # Amazon Linux
# or: sudo apt install python3-pip  # Ubuntu

# Set up agent
mkdir -p ~/zinq-agent && cd ~/zinq-agent
python3 -m venv venv
source venv/bin/activate
pip install zinq-agent[webhook]

# Copy agent code
nano my_agent.py
```

### Step 3: Set up systemd (same as Linux section)

### Step 4: Set your webhook URL

`http://YOUR_EC2_IP:8080/webhook`

---

## Railway (One-Click Deploy)

[Railway](https://railway.app/) is the easiest way to deploy a webhook agent. Free tier includes 500 hours/month.

### Step 1: Prepare your repo

```
my-zinq-agent/
  my_agent.py
  requirements.txt
  Procfile
```

**requirements.txt:**
```
zinq-agent[webhook]>=0.1.0
```

**Procfile:**
```
web: python my_agent.py
```

Make sure your agent reads `PORT` from environment for Railway's dynamic port:

```python
import os

port = int(os.environ.get("PORT", 8080))
webhook.start(port=port)
```

### Step 2: Deploy

1. Push to GitHub
2. Go to [railway.app](https://railway.app/) and connect your repo
3. Set environment variables: `ZINQ_API_KEY`, `ZINQ_WEBHOOK_SECRET`
4. Railway gives you a URL like `https://my-agent.up.railway.app`
5. Set your webhook URL to: `https://my-agent.up.railway.app/webhook`

---

## Render (One-Click Deploy)

[Render](https://render.com/) offers a free tier for web services.

### Step 1: Same repo structure as Railway

### Step 2: Deploy

1. Push to GitHub
2. Go to [render.com](https://render.com/) and create a new Web Service
3. Connect your repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `python my_agent.py`
6. Set environment variables
7. Set your webhook URL to the Render URL + `/webhook`

---

## Fly.io (One-Click Deploy)

[Fly.io](https://fly.io/) has a generous free tier and global edge deployment.

### fly.toml

```toml
app = "my-zinq-agent"
primary_region = "ord"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
```

### Deploy

```bash
fly launch
fly secrets set ZINQ_API_KEY=zak_your_key # ZINQ_WEBHOOK_SECRET — not yet available
fly deploy
```

Your webhook URL: `https://my-zinq-agent.fly.dev/webhook`

---

## Multiple Agents on One Machine

You can run multiple agents on the same machine. Each agent is a separate Python process with its own `ZINQ_API_KEY`.

**Polling agents** (no webhook) have no port conflicts — just run them with different API keys:

```bash
# Terminal 1
ZINQ_API_KEY=zak_agent_one python agent_one.py

# Terminal 2
ZINQ_API_KEY=zak_agent_two python agent_two.py
```

**Webhook agents** each need a unique port — the kernel only allows one process per port:

```bash
# Agent 1 on port 8082
ZINQ_API_KEY=zak_agent_one PORT=8082 python agent_one.py

# Agent 2 on port 8083
ZINQ_API_KEY=zak_agent_two PORT=8083 python agent_two.py
```

For systemd, create a separate service file per agent:

```bash
sudo cp zinq-agent.service /etc/systemd/system/zinq-agent-one.service
sudo cp zinq-agent.service /etc/systemd/system/zinq-agent-two.service
# Edit each with its own ZINQ_API_KEY and PORT
```

Each agent appears as a separate contact in the Zinq app with its own chat thread.

---

## Production Checklist

Before going to production, make sure you:

- [ ] **Never skip signature verification** -- remove `skip_signature_check=True`
- [ ] **Use environment variables** for secrets -- never hardcode API keys
- [ ] **Set up logging** -- add Python logging so you can debug issues
- [ ] **Handle errors gracefully** -- send a friendly vibe on failure, don't crash
- [ ] **Use a production WSGI server** -- use gunicorn instead of the built-in Flask server
- [ ] **Monitor credits** -- check `agent.user.context().credit_status` before expensive operations
- [ ] **Set restart policies** -- use `Restart=always` (systemd) or `--restart unless-stopped` (Docker)
- [ ] **Use HTTPS** -- put your agent behind a reverse proxy (nginx, Caddy) with TLS
- [ ] **Test the health endpoint** -- `curl https://your-server.com/health` should return `{"status": "ok"}`

### Production webhook server

For production, use gunicorn instead of the built-in Flask development server:

```python
# my_agent.py
from zinq_agent import ZinqAgent, ZinqWebhook

agent = ZinqAgent()
webhook = ZinqWebhook(secret="dev", skip_signature_check=True  # Signature verification coming soon)

@webhook.on("vibe.received")
def handle(event):
    agent.vibes.send(text=f"Got: {event.data.text}")

# Create the Flask app for gunicorn
app = webhook.create_flask_app()
```

```bash
pip install gunicorn
gunicorn -b 0.0.0.0:8080 -w 1 --timeout 30 my_agent:app
```

> Use `-w 1` (single worker) to avoid duplicate processing. If you need multiple workers, make your handlers idempotent.
