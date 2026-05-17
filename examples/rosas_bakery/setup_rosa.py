#!/usr/bin/env python3
"""Deploy Rosa's Bakery agent and load menu data.

Usage:
    export ZINQ_BIZ_KEY=zbk_your_key
    python setup_rosa.py
"""

import os
from zinq_agent import ZinqMarketplaceAdmin

API_KEY = os.environ.get("ZINQ_BIZ_KEY", "")
if not API_KEY:
    print("ERROR: Set ZINQ_BIZ_KEY first")
    exit(1)

ROSA_SERVER_HOST = os.environ.get("ROSA_SERVER_HOST", "")
ROSA_SERVER_PORT = os.environ.get("ROSA_SERVER_PORT", "8081")

if not ROSA_SERVER_HOST:
    print("ERROR: Set ROSA_SERVER_HOST to the public IP of the machine running rosa_server.py")
    exit(1)

admin = ZinqMarketplaceAdmin(api_key=API_KEY, base_url="https://zinq-app.com/api")

# Deploy agent — substitute server host/port in YAML
with open("rosa.yaml") as f:
    yaml_content = f.read()
yaml_content = yaml_content.replace("${ROSA_SERVER_HOST}", ROSA_SERVER_HOST)
yaml_content = yaml_content.replace("${ROSA_SERVER_PORT}", ROSA_SERVER_PORT)
admin.agent.deploy(yaml_content)
print("Agent deployed")

# Load menu
menu = [
    {"name": "Espresso", "price": 3.50, "category": "drinks", "description": "Double shot, rich and bold"},
    {"name": "Cappuccino", "price": 4.50, "category": "drinks", "description": "Espresso with steamed milk foam"},
    {"name": "Latte", "price": 5.00, "category": "drinks", "description": "Smooth espresso with steamed milk"},
    {"name": "Croissant", "price": 3.00, "category": "pastry", "description": "Buttery, flaky — Rosa's famous"},
    {"name": "Pain au Chocolat", "price": 3.50, "category": "pastry", "description": "Chocolate-filled croissant"},
    {"name": "Everything Bagel", "price": 4.00, "category": "bread", "description": "Toasted with cream cheese"},
    {"name": "Sourdough Loaf", "price": 7.50, "category": "bread", "description": "24-hour fermented, crusty"},
    {"name": "Egg & Cheese Sandwich", "price": 6.50, "category": "hot", "description": "Scrambled eggs, cheddar, brioche bun"},
    {"name": "Avocado Toast", "price": 8.00, "category": "hot", "description": "Sourdough, smashed avo, chili flakes"},
]

for item in menu:
    admin.data.add("menu", item)
    print(f"  Added: {item['name']}")

print(f"\nMenu loaded: {len(menu)} items")
print("\nTest with:")
print('  admin.test.chat("What do you have?")')
print('  admin.test.chat("Any specials today?")')
print('  admin.test.chat("I\'ll take a croissant and a latte")')
