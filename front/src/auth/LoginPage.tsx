import { useState, type FormEvent } from "react";
import { ApiError } from "../api";
import { Link, useRouter } from "../router";
import { useAuth } from "./useAuth";
import "./auth.css";
import { Logo } from "../components/Logo";

export function LoginPage() {
  const { signIn } = useAuth();
  const { navigate } = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const { onboardingCompleted } = await signIn(login.trim(), password);
      navigate(onboardingCompleted ? "/" : "/onboarding", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.detail : "Не удалось войти. Попробуйте ещё раз.");
      setPending(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-panel">
        <header className="auth-header">
          <Logo className="auth-logo" />
          <p className="auth-brand">Альфа · Лента</p>
        </header>

        <div className="auth-intro">
          <h1>Вход</h1>
          <p>Новости, которые влияют на ваш бизнес — с оценкой риска и возможностей.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Логин</span>
            <input
              value={login}
              onChange={(event) => setLogin(event.target.value)}
              autoComplete="username"
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
              autoComplete="current-password"
              required
            />
          </label>

          {error ? <p className="auth-error">{error}</p> : null}

          <button type="submit" className="button button--primary" disabled={pending}>
            {pending ? "Входим…" : "Войти"}
          </button>
        </form>

        <div className="auth-divider" aria-hidden="true">
          <span>или</span>
        </div>

        <Link to="/register" className="button button--ghost button--block">
          Зарегистрироваться
        </Link>

        <p className="auth-demo">Демо-доступ: demo_full / demo</p>
      </div>
    </div>
  );
}
