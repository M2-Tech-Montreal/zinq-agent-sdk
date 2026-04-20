# E2E Tests

End-to-end tests that run against the real dev server to verify the full
Zinq Agent SDK stack. Each test file mirrors an SDK example or sub-client.

## Prerequisites

1. A personal agent API key (`zak_...`)
2. A marketplace admin API key (`zbk_...`)
3. Python 3.10+ with `pytest` installed

## Setup

```bash
# Required
export ZINQ_TEST_API_KEY=zak_your_test_key
export ZINQ_TEST_BIZ_KEY=zbk_your_test_key

# Optional (defaults to https://zinq-app.com/dev-api)
export ZINQ_DEV_URL=https://zinq-app.com/dev-api
```

## Run

```bash
# Install dependencies
pip install pytest

# Run all E2E tests
pytest tests/e2e/ -v

# Run a specific test file
pytest tests/e2e/test_personal_agent.py -v

# Run a specific test class
pytest tests/e2e/test_personal_agent.py::TestMemories -v

# Run a single test
pytest tests/e2e/test_personal_agent.py::TestMemories::test_save_and_get_memory -v

# Only personal agent tests (no marketplace key needed)
pytest tests/e2e/test_personal_agent.py tests/e2e/test_sentinel_example.py tests/e2e/test_trading_example.py -v

# Only marketplace tests
pytest tests/e2e/test_marketplace_agent.py tests/e2e/test_bakery_example.py tests/e2e/test_barber_example.py tests/e2e/test_nutrition_example.py -v
```

## Create Test Keys

### Personal Agent Key

1. Open the Zinq app
2. Go to My Agents
3. Create an agent (or use an existing one)
4. Copy the API key (`zak_...`)

### Marketplace Admin Key

1. Open the Zinq app
2. Go to My Agents > Create Marketplace Agent
3. Complete the setup flow
4. Copy the business API key (`zbk_...`)

## Test Structure

| File | What it tests | Key required |
|------|--------------|--------------|
| `test_personal_agent.py` | All ZinqAgent sub-clients (diary, vibes, feed, contacts, zones, memories, user, gemini, billing) | `ZINQ_TEST_API_KEY` |
| `test_marketplace_agent.py` | Full ZinqMarketplaceAdmin lifecycle (agent, data, conversations, reviews, broadcast, billing, test) | `ZINQ_TEST_BIZ_KEY` |
| `test_sentinel_example.py` | Sentinel email/Slack personal agent pattern | `ZINQ_TEST_API_KEY` |
| `test_trading_example.py` | Trading bot personal agent pattern | `ZINQ_TEST_API_KEY` |
| `test_bakery_example.py` | Rosa's Bakery business agent pattern | `ZINQ_TEST_BIZ_KEY` |
| `test_barber_example.py` | Joe's Barber business agent pattern | `ZINQ_TEST_BIZ_KEY` |
| `test_nutrition_example.py` | Dr. Sarah Nutrition business agent pattern | `ZINQ_TEST_BIZ_KEY` |

## Notes

- Tests that require existing data (contacts, conversations) will skip
  gracefully if the data does not exist.
- Memory and data collection tests clean up after themselves.
- Gemini tests consume a small number of credits from the test user's account.
- Tests create unique keys/collection names to avoid collisions when
  run in parallel or repeatedly.
