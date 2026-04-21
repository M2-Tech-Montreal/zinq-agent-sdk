#!/bin/bash
# Start Rosa's Bakery — mock server + deploy agent + load menu

export ZINQ_BIZ_KEY=zbk_392aeea6c76a9cd87b3baf75d83a8e796637e5c2a9284da8fdb91c4b2c88c217

cd "$(dirname "$0")"

# Generate SSL cert if missing
if [ ! -f cert.pem ]; then
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=34.58.243.153"
fi

# Deploy agent + load menu
python3 setup_rosa.py

# Start mock server (foreground)
python3 rosa_server.py
