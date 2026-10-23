import { useState, type FormEvent } from "react";
import { ApiError } from "../api";
import { Link, useRouter } from "../router";
import { useAuth } from "./useAuth";
import "./auth.css";

export function RegisterPage() {
  const { signUp } = useAuth();
  const { navigate } = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (password !== repeat) {
      setError("Пароли не совпадают");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await signUp(login.trim(), password);
      navigate("/onboarding", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : "Не удалось зарегистрироваться.");
      setPending(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-panel">
        <header className="auth-header">
          <span className="auth-logo" aria-hidden="true">
            А
          </span>
          <p className="auth-brand">Альфа · Лента</p>
        </header>

        <div className="auth-intro">
          <h1>Регистрация</h1>
          <p>Создайте аккаунт и подключите бизнес из данных Альфа-Банка.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Логин</span>
            <input
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              autoComplete="username"
              minLength={3}
              required
              autoFocus
            />
          </label>
          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </label>
          <label className="field">
            <span>Повторите пароль</span>
            <input
              type="password"
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              autoComplete="new-password"
              minLength={6}
              required
            />
          </label>

          {error ? <p className="auth-error">{error}</p> : null}

          <button type="submit" className="button button--primary" disabled={pending}>
            {pending ? "Создаём аккаунт…" : "Зарегистрироваться"}
          </button>
        </form>

        <div className="auth-divider" aria-hidden="true">
          <span>или</span>
        </div>

        <Link to="/login" className="button button--ghost button--block">
          Войти
        </Link>
      </div>
    </div>
  );
}
