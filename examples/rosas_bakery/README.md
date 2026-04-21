# Rosa's Bakery — Marketplace Agent Example

A complete marketplace agent with static menu + external tools for live specials and orders.

## Setup

### 1. Generate SSL cert (for the mock server)

```bash
cd examples/rosas_bakery
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=34.58.243.153"
```

### 2. Start the mock bakery server

```bash
python rosa_server.py
```

Runs on `https://0.0.0.0:8081` with endpoints:
- `/specials` — today's specials
- `/inventory` — item availability
- `/orders` — place an order
- `/wait-time` — estimated wait

### 3. Deploy the agent

```bash
export ZINQ_BIZ_KEY=zbk_your_key
python setup_rosa.py
```

### 4. Test

```python
from zinq_agent import ZinqMarketplaceAdmin
admin = ZinqMarketplaceAdmin(api_key="zbk_...")
admin.test.chat("What do you have?")
admin.test.chat("Any specials today?")
admin.test.chat("I'll take a croissant and a latte")
```

## Architecture

- **Static menu** — stored in Zinq collections via `setup_rosa.py`, never changes
- **Specials** — external tool calls Rosa's server, she updates her database
- **Orders** — external tool POSTs to Rosa's server with userId
- **Memory** — Gemini remembers customer preferences (oat milk, allergies, usual order)
- **Two-part prompt** — system prompt (tools/memory) injected by Zinq + Rosa's personality from YAML

## Files

| File | What |
|------|------|
| `rosa.yaml` | Agent definition — personality, tools, collections |
| `rosa_server.py` | Mock bakery backend (specials, inventory, orders) |
| `setup_rosa.py` | Deploy agent + load menu data via SDK |
