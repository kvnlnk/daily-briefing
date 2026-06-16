# P3 — Delivery Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Define DeliveryProtocol + concrete senders (stdout, ntfy). Wire delivery config from brief.yaml. Every run always delivers to stdout as fallback.

**Architecture:** Abstract base in delivery/base.py. Sender implementations in delivery/senders/. Factory selection via brief.yaml delivery[] entries.

---

### Task 1: Create DeliveryProtocol base

- [ ] Create `daily_briefing/delivery/__init__.py`
- [ ] Create `daily_briefing/delivery/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class DeliveryResult:
    success: bool
    channel: str
    error: str | None = None

class DeliveryProtocol(ABC):
    name: str = ""
    @abstractmethod
    def send(self, message: str, **kwargs) -> DeliveryResult: ...
```

- [ ] Step 1: Write failing test → Step 2: Implement → Step 3: Pass → Step 4: Commit

---

### Task 2: Create stdout sender (zero-config default)

- [ ] Create `daily_briefing/delivery/senders/__init__.py`
- [ ] Create `daily_briefing/delivery/senders/stdout.py`

```python
class StdoutSender(DeliveryProtocol):
    name = "stdout"
    def send(self, message: str, **kwargs) -> DeliveryResult:
        click.echo(message)
        return DeliveryResult(success=True, channel="stdout")
```

- [ ] Test: invokes click.echo with message → Commit

---

### Task 3: Create ntfy sender

- [ ] Create `daily_briefing/delivery/senders/ntfy_sender.py`

```python
import os, requests

NTFY_DEFAULT_SERVER = "https://ntfy.sh"

class NtfySender(DeliveryProtocol):
    name = "ntfy"
    def send(self, message: str, topic: str = "", server: str = "", **kwargs) -> DeliveryResult:
        topic = topic or os.environ.get("NTFY_TOPIC", "")
        if not topic:
            return DeliveryResult(success=False, channel="ntfy", error="NTFY_TOPIC not set")
        server = server or NTFY_DEFAULT_SERVER
        try:
            resp = requests.post(f"{server}/{topic}", data=message.encode("utf-8"), timeout=10)
            resp.raise_for_status()
            return DeliveryResult(success=True, channel=f"ntfy:{topic}")
        except requests.RequestException as e:
            return DeliveryResult(success=False, channel="ntfy", error=str(e))
```

- [ ] Test with mocked HTTP → Commit

---

### Task 4: Create DeliveryFactory

- [ ] Modify `daily_briefing/delivery/__init__.py`

```python
def get_delivery(method: str) -> DeliveryProtocol:
    """Get a delivery sender by method name."""
    senders = {"stdout": StdoutSender, "ntfy": NtfySender}
    cls = senders.get(method)
    if not cls:
        raise ValueError(f"Unknown delivery method: {method}")
    return cls()
```

- [ ] Test factory with known/unknown methods → Commit

---

### Task 5: Wire delivery into CLI main

**In `cli.py`**, after summarizer:
```python
from daily_briefing.delivery import get_delivery as get_sender

delivery_configs = configuration.raw.get("delivery", [{"method": "stdout"}])
if not delivery_configs:
    delivery_configs = [{"method": "stdout"}]  # always fall back

for dc in delivery_configs:
    method = dc.get("method", "stdout")
    try:
        sender = get_sender(method)
        # Pass all extra config keys as kwargs
        kwargs = {k: v for k, v in dc.items() if k != "method"}
        result = sender.send(summary.text, **kwargs)
        if not result.success:
            click.echo(f"Delivery failed ({method}): {result.error}", err=True)
    except ValueError as e:
        click.echo(f"Unknown delivery method: {method}", err=True)
```

**Config reading: update BriefingConfig or just use raw**.

The `delivery:` block in brief.yaml:
```yaml
delivery:
  - method: stdout
  - method: ntfy
    topic: my-briefing
```

- [ ] Step 1: Write CLI test for delivery flow
- [ ] Step 2: Wire delivery into main
- [ ] Step 3: Test: `python -m daily_briefing` delivers to stdout
- [ ] Step 4: Commit
