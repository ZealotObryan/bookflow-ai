import httpx


class TumaSendError(RuntimeError):
    """Raised when TumaSend rejects a message or cannot be reached."""


class TumaSendClient:
    def __init__(
        self,
        api_key: str | None,
        sms_sender_id: str | None,
        base_url: str = "https://gateway.tumasend.com",
    ) -> None:
        if not api_key:
            raise TumaSendError("TumaSend API key is not configured")
        self.api_key = api_key
        self.sms_sender_id = sms_sender_id
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/{path}",
                headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=httpx.Timeout(10.0, connect=3.0),
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise TumaSendError("TumaSend request failed") from exc
        if not isinstance(data, dict) or data.get("success") is False:
            raise TumaSendError("TumaSend did not accept the message")
        batch_id = data.get("batch_id")
        if not isinstance(batch_id, str) or not batch_id:
            raise TumaSendError("TumaSend response did not contain a batch identifier")
        return data

    def send_whatsapp(self, phone_e164: str, message: str) -> str:
        result = self._post("send/whatsapp", {"recipients": [phone_e164], "message": message})
        return str(result["batch_id"])

    def send_sms(self, phone_e164: str, message: str) -> str:
        if not self.sms_sender_id:
            raise TumaSendError("TumaSend SMS sender ID is not configured")
        result = self._post(
            "send/sms",
            {"from": self.sms_sender_id, "recipients": [phone_e164], "message": message},
        )
        return str(result["batch_id"])
