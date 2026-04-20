# Sentinel — TODO

## Send emails via Gmail
- Add `gmail.send` scope to OAuth
- Re-auth both accounts with new scope
- Add `send_email(account, to, subject, body)` to `gmail_monitor.py`
- Gemini detects "reply to Dan" or "email John about X" and triggers send
- User confirms before sending ("Send this? [preview]")
