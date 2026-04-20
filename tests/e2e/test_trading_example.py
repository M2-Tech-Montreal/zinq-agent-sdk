"""E2E tests for the Trading Bot personal agent example.

The trading bot monitors crypto positions and sends portfolio summaries,
price alerts, and uses Gemini for market analysis. These tests exercise
the SDK methods that the trading bot uses.
"""

from __future__ import annotations

import uuid

import pytest

from zinq_agent import ZinqAgent
from zinq_agent.models import GeminiResponse, Memory, VibeSendResult


class TestTradingPortfolio:
    """Tests covering the trading bot's portfolio summary flow."""

    def test_portfolio_summary_vibe(self, agent: ZinqAgent) -> None:
        """Trading bot sends a formatted portfolio summary."""
        summary = (
            "Portfolio: $12,450.00\n"
            "  BTC: $8,200.00 (+2.3%)\n"
            "  ETH: $4,250.00 (-0.8%)\n\n"
            "Daily range: $12,100 -- $12,600"
        )
        result = agent.vibes.send(text=summary)
        assert isinstance(result, VibeSendResult)
        assert result.vibe_id > 0

    def test_price_alert_vibe(self, agent: ZinqAgent) -> None:
        """Trading bot sends a price movement alert."""
        alert = (
            "BTC is up 5.2%\n"
            "$64,200.00 -> $67,538.40\n"
            "Volume: $1.2B (24h)"
        )
        result = agent.vibes.send(text=alert)
        assert isinstance(result, VibeSendResult)

    def test_daily_reset_vibe(self, agent: ZinqAgent) -> None:
        """Trading bot announces a new trading day."""
        result = agent.vibes.send(
            text="New day! Portfolio starting at $12,450.00"
        )
        assert isinstance(result, VibeSendResult)

    def test_help_menu_vibe(self, agent: ZinqAgent) -> None:
        """Trading bot sends a help menu with capabilities."""
        result = agent.vibes.send(
            text=(
                "I can help with:\n"
                "  \"How's my portfolio?\" -- current holdings\n"
                "  \"BTC price\" -- any coin price\n"
                "  \"Today's summary\" -- P&L recap\n"
                "  I auto-alert on 5%+ moves every 5 min"
            ),
        )
        assert isinstance(result, VibeSendResult)


class TestTradingMemory:
    """Tests covering the trading bot's price and alert memory."""

    def test_save_price_memories(self, agent: ZinqAgent) -> None:
        """Trading bot saves last known prices to memory."""
        btc_key = f"trading_btc_{uuid.uuid4().hex[:6]}"
        eth_key = f"trading_eth_{uuid.uuid4().hex[:6]}"

        agent.memories.save(btc_key, "67500.00", category="prices")
        agent.memories.save(eth_key, "3200.00", category="prices")

        prices = agent.memories.list(category="prices")
        assert isinstance(prices, list)
        assert len(prices) >= 2

        keys = {m.key for m in prices}
        assert btc_key in keys
        assert eth_key in keys

        # Cleanup
        agent.memories.delete(btc_key)
        agent.memories.delete(eth_key)

    def test_save_alert_memory(self, agent: ZinqAgent) -> None:
        """Trading bot saves a triggered alert to memory."""
        key = f"trading_alert_{uuid.uuid4().hex[:6]}"
        agent.memories.save(
            key,
            "BTC up 5.2% at 14:30 UTC -- $64,200 -> $67,538",
            category="price_alerts",
        )

        mem = agent.memories.get(key)
        assert mem is not None
        assert "BTC" in mem.value
        assert mem.category == "price_alerts"

        # Cleanup
        agent.memories.delete(key)

    def test_update_price_memory(self, agent: ZinqAgent) -> None:
        """Trading bot updates a price via upsert."""
        key = f"trading_price_{uuid.uuid4().hex[:6]}"

        r1 = agent.memories.save(key, "64200.00", category="prices")
        assert r1.created is True

        r2 = agent.memories.save(key, "67500.00", category="prices")
        assert r2.created is False

        mem = agent.memories.get(key)
        assert mem is not None
        assert mem.value == "67500.00"

        # Cleanup
        agent.memories.delete(key)

    def test_list_alerts_by_category(self, agent: ZinqAgent) -> None:
        """Trading bot lists all historical alerts."""
        key = f"trading_hist_{uuid.uuid4().hex[:6]}"
        agent.memories.save(key, "ETH down 6.1%", category="e2e_alerts")

        alerts = agent.memories.list(category="e2e_alerts")
        assert isinstance(alerts, list)
        assert any(m.key == key for m in alerts)

        # Cleanup
        agent.memories.delete(key)


class TestTradingGemini:
    """Tests covering the trading bot's Gemini-powered analysis."""

    def test_gemini_market_analysis(self, agent: ZinqAgent) -> None:
        """Trading bot asks Gemini for market sentiment analysis."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are a crypto market analyst. Be concise.",
                },
                {
                    "role": "user",
                    "content": (
                        "BTC dropped 5% in 1 hour from $67,500 to $64,125. "
                        "ETH followed down 3%. Should I be concerned?"
                    ),
                },
            ],
            model="flash",
            max_tokens=200,
        )
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0

    def test_gemini_parse_coin_ticker(self, agent: ZinqAgent) -> None:
        """Trading bot uses Gemini to extract a coin ticker from user text."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract the cryptocurrency ticker symbol from this message. "
                        "Reply with just the symbol (e.g., BTC, ETH, SOL). "
                        "If none found, reply NONE."
                    ),
                },
                {"role": "user", "content": "What's the price of ethereum right now?"},
            ],
            model="flash",
            max_tokens=10,
        )
        assert isinstance(response, GeminiResponse)
        text = response.text.strip().upper()
        assert text in ("ETH", "ETHEREUM")

    def test_gemini_parse_alert_request(self, agent: ZinqAgent) -> None:
        """Trading bot uses Gemini to parse a custom alert request."""
        response = agent.gemini.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Parse this alert request. Extract: coin (ticker), "
                        "direction (up/down/both), threshold (percentage). "
                        "Reply as JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": "Alert me if SOL goes up more than 10%",
                },
            ],
            model="flash",
            max_tokens=100,
        )
        assert isinstance(response, GeminiResponse)
        assert len(response.text) > 0


class TestTradingPolling:
    """Tests covering the polling-based command loop pattern."""

    def test_check_received_vibes(self, agent: ZinqAgent) -> None:
        """Trading bot polls for user commands via received vibes."""
        vibes = agent.vibes.received(limit=5, unread=True)
        assert isinstance(vibes, list)

    def test_send_and_check_round_trip(self, agent: ZinqAgent) -> None:
        """Send a vibe and verify the send result."""
        result = agent.vibes.send(text="E2E trading round-trip test")
        assert result.vibe_id > 0
        assert result.push_sent is True or result.push_sent is False
