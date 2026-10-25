import asyncio
import logging
import secrets
from dataclasses import dataclass, field

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeEmptyError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)

from .config import Settings

logger = logging.getLogger(__name__)

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Настройка Telegram-твинка</title>
<style>
  :root { color-scheme: dark; --bg:#0b0b0b; --card:#171717; --line:#2a2a2a; --text:#f5f5f5; --muted:#9a9a9a; --accent:#ef3124; }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; display:grid; place-items:center; padding:24px; background:var(--bg); color:var(--text); font:15px/1.5 ui-sans-serif,system-ui,sans-serif; }
  main { width:min(100%,520px); padding:28px; border:1px solid var(--line); border-radius:24px; background:var(--card); }
  h1 { margin:0 0 8px; font-size:26px; letter-spacing:-.6px; }
  p { margin:0 0 20px; color:var(--muted); }
  label { display:block; margin:16px 0 6px; font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }
  input { width:100%; height:48px; padding:0 16px; border:1px solid var(--line); border-radius:14px; background:#0f0f0f; color:var(--text); font:inherit; outline:none; }
  input:focus { border-color:#555; }
  button { width:100%; height:48px; margin-top:14px; border:0; border-radius:14px; background:var(--text); color:#111; font:inherit; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.4; cursor:default; }
  button.secondary { background:#242424; color:var(--text); }
  .status { padding:12px 14px; border:1px solid var(--line); border-radius:14px; background:#101010; font-size:14px; }
  .status.error { border-color:#5a2424; color:#ffb4ad; }
  .status.ready { border-color:#245a37; color:#a7f3c5; }
  .hidden { display:none; }
  .row { display:flex; gap:8px; }
  .row button { margin-top:0; }
</style>
</head>
<body>
<main>
  <h1>Настройка Telegram-твинка</h1>
  <p>Сервис не авторизован. Введите сервисный токен, запросите код и подтвердите вход. После успеха сессия сохранится в state-папке.</p>
  <div id="status" class="status">Ожидание токена…</div>

  <div id="token-block">
    <label for="token">INGEST_TOKEN</label>
    <input id="token" type="password" autocomplete="off" placeholder="Сервисный токен">
    <button id="save-token">Продолжить</button>
  </div>

  <div id="start-block" class="hidden">
    <button id="start">Отправить код в Telegram</button>
  </div>

  <div id="code-block" class="hidden">
    <label for="code">Код из Telegram</label>
    <input id="code" inputmode="numeric" autocomplete="one-time-code" placeholder="12345">
    <button id="verify">Подтвердить</button>
    <button id="resend" class="secondary">Запросить код заново</button>
  </div>

  <div id="password-block" class="hidden">
    <label for="password">Пароль 2FA</label>
    <input id="password" type="password" autocomplete="current-password">
    <button id="signin-password">Войти</button>
  </div>

  <div id="done-block" class="hidden">
    <button id="close" class="secondary">Готово, можно закрыть</button>
  </div>
</main>
<script>
(() => {
  const $ = (id) => document.getElementById(id);
  let token = sessionStorage.getItem("tgSetupToken") || "";
  let status = "idle";

  const setStatus = (text, kind = "") => {
    const el = $("status");
    el.textContent = text;
    el.className = "status" + (kind ? " " + kind : "");
  };

  const show = (id, visible) => $(id).classList.toggle("hidden", !visible);

  const render = () => {
    show("token-block", !token);
    show("start-block", Boolean(token) && status !== "needs_code" && status !== "needs_password" && status !== "authorized");
    show("code-block", Boolean(token) && status === "needs_code");
    show("password-block", Boolean(token) && status === "needs_password");
    show("done-block", Boolean(token) && status === "authorized");
  };

  const api = async (path, body) => {
    const response = await fetch(path, {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json", "X-Ingest-Token": token },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || data.detail || "Ошибка " + response.status);
    return data;
  };

  const apply = (data) => {
    status = data.status || "idle";
    if (status === "authorized") {
      setStatus("Готово. Твинк авторизован.", "ready");
    } else if (status === "needs_password") {
      setStatus("Код принят. Введите пароль двухфакторной аутентификации.");
    } else if (status === "needs_code") {
      setStatus("Код отправлен в Telegram. Введите его ниже.");
    } else {
      setStatus(data.error || "Готов к настройке.");
    }
    render();
  };

  const refresh = async () => {
    if (!token) return;
    try {
      apply(await api("/api/setup/status"));
    } catch (error) {
      setStatus(error.message, "error");
      if (String(error.message).includes("токен")) {
        token = "";
        render();
      }
    }
  };

  $("save-token").onclick = () => {
    token = $("token").value.trim();
    if (!token) return;
    sessionStorage.setItem("tgSetupToken", token);
    void refresh();
  };

  $("start").onclick = async () => {
    $("start").disabled = true;
    try {
      apply(await api("/api/setup/start", {}));
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      $("start").disabled = false;
    }
  };

  $("resend").onclick = () => $("start").onclick();

  $("verify").onclick = async () => {
    const code = $("code").value.trim();
    if (!code) return;
    $("verify").disabled = true;
    try {
      apply(await api("/api/setup/verify", { code }));
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      $("verify").disabled = false;
    }
  };

  $("signin-password").onclick = async () => {
    const password = $("password").value;
    if (!password) return;
    $("signin-password").disabled = true;
    try {
      apply(await api("/api/setup/password", { password }));
    } catch (error) {
      setStatus(error.message, "error");
    } finally {
      $("signin-password").disabled = false;
    }
  };

  $("close").onclick = () => window.close();

  if (token) void refresh();
  else render();
  setInterval(() => { if (token && status !== "authorized") void refresh(); }, 3000);
})();
</script>
</body>
</html>
"""


@dataclass
class SetupState:
    client: TelegramClient
    settings: Settings
    status: str = "idle"
    error: str = ""
    phone_code_hash: str | None = None
    authenticated: asyncio.Event = field(default_factory=asyncio.Event)


def _masked_phone(phone: str) -> str:
    if len(phone) < 6:
        return phone
    return f"{phone[:2]}{'*' * (len(phone) - 4)}{phone[-2:]}"


def _authorized(state: SetupState) -> None:
    state.status = "authorized"
    state.error = ""
    state.authenticated.set()
    try:
        state.client.session.save()
    except Exception:
        logger.debug("session save failed", exc_info=True)
    logger.info("telegram twin authorized via setup ui")


def _token_ok(request: Request, settings: Settings) -> bool:
    supplied = request.headers.get("x-ingest-token", "")
    return bool(settings.ingest_token) and secrets.compare_digest(
        supplied, settings.ingest_token
    )


async def _payload(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def create_setup_app(state: SetupState) -> Starlette:
    settings = state.settings

    async def page(_: Request) -> HTMLResponse:
        return HTMLResponse(PAGE)

    async def status(request: Request) -> JSONResponse:
        if not _token_ok(request, settings):
            return JSONResponse({"error": "Неверный сервисный токен"}, status_code=401)
        return JSONResponse(
            {
                "status": state.status,
                "error": state.error,
                "phone": _masked_phone(settings.phone),
            }
        )

    async def start(request: Request) -> JSONResponse:
        if not _token_ok(request, settings):
            return JSONResponse({"error": "Неверный сервисный токен"}, status_code=401)
        if state.status == "authorized":
            return JSONResponse({"status": state.status})
        try:
            sent = await state.client.send_code_request(settings.phone)
            state.phone_code_hash = sent.phone_code_hash
            state.status = "needs_code"
            state.error = ""
        except FloodWaitError as exc:
            state.error = f"Telegram просит подождать {exc.seconds} секунд"
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=429
            )
        except Exception as exc:
            state.error = str(exc)
            logger.exception("telegram setup: send code failed")
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=400
            )
        return JSONResponse({"status": state.status, "phone": _masked_phone(settings.phone)})

    async def verify(request: Request) -> JSONResponse:
        if not _token_ok(request, settings):
            return JSONResponse({"error": "Неверный сервисный токен"}, status_code=401)
        if state.status == "authorized":
            return JSONResponse({"status": state.status})
        payload = await _payload(request)
        code = str(payload.get("code") or "").strip()
        if not code:
            return JSONResponse({"error": "Введите код из Telegram"}, status_code=400)
        if not state.phone_code_hash:
            return JSONResponse(
                {"error": "Сначала запросите код", "status": state.status}, status_code=400
            )
        try:
            await state.client.sign_in(
                phone=settings.phone,
                code=code,
                phone_code_hash=state.phone_code_hash,
            )
        except SessionPasswordNeededError:
            state.status = "needs_password"
            state.error = ""
            return JSONResponse({"status": state.status})
        except (PhoneCodeInvalidError, PhoneCodeExpiredError, PhoneCodeEmptyError):
            state.error = "Код не подошёл. Запросите новый код или попробуйте снова."
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=400
            )
        except Exception as exc:
            state.error = str(exc)
            logger.exception("telegram setup: sign in failed")
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=400
            )
        _authorized(state)
        return JSONResponse({"status": state.status})

    async def password(request: Request) -> JSONResponse:
        if not _token_ok(request, settings):
            return JSONResponse({"error": "Неверный сервисный токен"}, status_code=401)
        if state.status == "authorized":
            return JSONResponse({"status": state.status})
        payload = await _payload(request)
        secret = str(payload.get("password") or "")
        if not secret:
            return JSONResponse({"error": "Введите пароль 2FA"}, status_code=400)
        if state.status != "needs_password":
            return JSONResponse(
                {"error": "Сначала подтвердите код", "status": state.status}, status_code=400
            )
        try:
            await state.client.sign_in(password=secret)
        except PasswordHashInvalidError:
            state.error = "Неверный пароль 2FA"
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=400
            )
        except Exception as exc:
            state.error = str(exc)
            logger.exception("telegram setup: password sign in failed")
            return JSONResponse(
                {"status": state.status, "error": state.error}, status_code=400
            )
        _authorized(state)
        return JSONResponse({"status": state.status})

    return Starlette(
        routes=[
            Route("/", page),
            Route("/setup", page),
            Route("/api/setup/status", status),
            Route("/api/setup/start", start, methods=["POST"]),
            Route("/api/setup/verify", verify, methods=["POST"]),
            Route("/api/setup/password", password, methods=["POST"]),
        ]
    )


async def run_setup(client: TelegramClient, settings: Settings) -> asyncio.Task:
    if not settings.ingest_token:
        raise SystemExit("INGEST_TOKEN обязателен для веб-настройки Telegram")
    if not settings.phone:
        raise SystemExit("TG_PHONE обязателен для веб-настройки Telegram")
    state = SetupState(client=client, settings=settings)
    config = uvicorn.Config(
        create_setup_app(state),
        host=settings.setup_host,
        port=settings.setup_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    logger.warning(
        "Telegram не авторизован. Откройте http://%s:%s/setup и введите INGEST_TOKEN",
        settings.setup_host,
        settings.setup_port,
    )
    try:
        if settings.setup_timeout_seconds > 0:
            await asyncio.wait_for(
                state.authenticated.wait(), timeout=settings.setup_timeout_seconds
            )
        else:
            await state.authenticated.wait()
    except TimeoutError:
        task.cancel()
        raise SystemExit("Время ожидания настройки Telegram истекло") from None
    logger.info("Telegram setup finished; starting ingest")
    return task
