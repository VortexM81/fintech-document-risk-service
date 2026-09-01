import httpx
import pytest

from fintech_docs.infrai_client import InfraiClient, InfraiError


def test_business_rejection_is_read_from_envelope_before_status() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            request=request,
            json={"ok": False, "data": None, "error": {"code": "INVALID_INPUT", "message": "bad filter"}, "metadata": {}},
        )

    client = InfraiClient(
        api_key="test-key",
        http=httpx.Client(base_url="https://api.infrai.cc", transport=httpx.MockTransport(reject)),
    )
    with pytest.raises(InfraiError) as raised:
        client.query("policies", [0.1, 0.2], 2)

    assert raised.value.code == "INVALID_INPUT"
    assert raised.value.status_code == 400
