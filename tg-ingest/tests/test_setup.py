from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from tg_ingest.config import Settings
from tg_ingest.setup import SetupState, create_setup_app

HEADERS = {"X-Ingest-Token": "secret"}


class FakeSession:
    def save(self) -> None:
        pass


class FakeClient:
    def __init__(self) -> None:
        self.session = FakeSession()

    async def send_code_request(self, phone: str) -> SimpleNamespace:
        return SimpleNamespace(phone_code_hash="code-hash")

    async def sign_in(self, **kwargs: object) -> None:
        if kwargs.get("code") != "12345":
            raise PhoneCodeInvalidError(request=None)


class TwoFactorClient(FakeClient):
    async def sign_in(self, **kwargs: object) -> None:
        if "password" in kwargs:
            if kwargs["password"] == "2fa":
                return
            raise PasswordHashInvalidError(request=None)
        raise SessionPasswordNeededError(request=None)


def _settings() -> Settings:
    return Settings(
        api_id=1,
        api_hash="hash",
        phone="+79990000000",
        ingest_token="secret",
        setup_enabled=True,
    )


def _app(client: FakeClient) -> tuple[object, SetupState]:
    state = SetupState(client=client, settings=_settings())  # type: ignore[arg-type]
    return create_setup_app(state), state


async def test_setup_page_and_token_guard() -> None:
    app, _ = _app(FakeClient())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        page = await http.get("/setup")
        assert page.status_code == 200
        assert "Настройка Telegram" in page.text

        denied = await http.get("/api/setup/status")
        assert denied.status_code == 401

        status = await http.get("/api/setup/status", headers=HEADERS)
        assert status.status_code == 200
        assert status.json()["status"] == "idle"


async def test_setup_code_flow() -> None:
    app, state = _app(FakeClient())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        started = await http.post("/api/setup/start", headers=HEADERS)
        assert started.status_code == 200
        assert started.json()["status"] == "needs_code"

        invalid = await http.post(
            "/api/setup/verify", headers=HEADERS, json={"code": "00000"}
        )
        assert invalid.status_code == 400

        verified = await http.post(
            "/api/setup/verify", headers=HEADERS, json={"code": "12345"}
        )
        assert verified.status_code == 200
        assert verified.json()["status"] == "authorized"
        assert state.authenticated.is_set()


async def test_setup_two_factor_flow() -> None:
    app, state = _app(TwoFactorClient())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        await http.post("/api/setup/start", headers=HEADERS)
        needs_password = await http.post(
            "/api/setup/verify", headers=HEADERS, json={"code": "12345"}
        )
        assert needs_password.status_code == 200
        assert needs_password.json()["status"] == "needs_password"

        wrong = await http.post(
            "/api/setup/password", headers=HEADERS, json={"password": "wrong"}
        )
        assert wrong.status_code == 400

        done = await http.post(
            "/api/setup/password", headers=HEADERS, json={"password": "2fa"}
        )
        assert done.status_code == 200
        assert done.json()["status"] == "authorized"
        assert state.authenticated.is_set()
