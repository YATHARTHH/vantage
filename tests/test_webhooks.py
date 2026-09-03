"""Unit tests for Enterprise Webhooks, HMAC signatures and SSRF firewall."""
import pytest
from vantage.services.webhook_notifier import (
    is_ssrf_blocked_url,
    compute_hmac_signature,
    WebhookNotifier,
)


def test_ssrf_firewall():
    # Blocked loopback and RFC1918 IPs in production mode (allow_dev_local=False)
    assert is_ssrf_blocked_url("http://127.0.0.1:8000/webhook", allow_dev_local=False) is True
    assert is_ssrf_blocked_url("http://localhost/webhook", allow_dev_local=False) is True
    assert is_ssrf_blocked_url("http://10.0.0.1/webhook", allow_dev_local=False) is True
    assert is_ssrf_blocked_url("http://169.254.169.254/latest/meta-data", allow_dev_local=False) is True

    # Valid public HTTPS endpoints
    assert is_ssrf_blocked_url("https://hooks.slack.com/services/XXX", allow_dev_local=False) is False
    assert is_ssrf_blocked_url("https://api.pagerduty.com/v2/enqueue", allow_dev_local=False) is False


def test_hmac_signature_generation():
    secret = "whsec_test_secret_12345"
    timestamp = 1700000000
    body = '{"event":"test"}'

    sig = compute_hmac_signature(secret, timestamp, body)
    assert sig.startswith("t=1700000000,v1=")
    assert len(sig) > 30


def test_webhook_subscription_registration():
    notifier = WebhookNotifier()
    sub = notifier.register_subscription(
        display_name="Slack Alerts",
        endpoint_url="https://hooks.slack.com/services/123",
        project_id="search-v2",
        provider="slack",
    )

    assert sub.webhook_id.startswith("wh_")
    assert sub.secret.startswith("whsec_")
    assert len(notifier.list_subscriptions("search-v2")) == 1
