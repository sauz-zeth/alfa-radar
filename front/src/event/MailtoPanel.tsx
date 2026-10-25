import { useMemo, useState, type FormEvent } from "react";
import type { FeedItemDetail } from "../api";
import { SectionHeader } from "./SectionHeader";
import "./event-mailto.css";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function actionKey(action: FeedItemDetail["actions"][number], index: number): string {
  return action.id ?? `action-${index}`;
}

function parseRecipients(value: string): { valid: string[]; invalid: string[] } {
  const items = value
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  const valid: string[] = [];
  const invalid: string[] = [];

  for (const item of items) {
    const email = item.match(/<([^>]+)>/)?.[1]?.trim() ?? item;
    if (EMAIL_RE.test(email)) valid.push(email);
    else invalid.push(item);
  }

  return { valid, invalid };
}

function defaultSubject(detail: FeedItemDetail, actionId: string): string {
  const index = detail.actions.findIndex((item, position) => actionKey(item, position) === actionId);
  const action = index >= 0 ? detail.actions[index] : undefined;
  return action ? `Поручение: ${action.title}` : `Поручение: ${detail.title}`;
}

function defaultBody(detail: FeedItemDetail, actionId: string): string {
  const index = detail.actions.findIndex((item, position) => actionKey(item, position) === actionId);
  const action = index >= 0 ? detail.actions[index] : undefined;
  const eventUrl =
    typeof window === "undefined" ? null : `${window.location.origin}/event/${detail.id}`;
  const lines = [
    "Здравствуйте!",
    "",
    `По событию «${detail.title}».`,
    detail.what_it_means ? `Что это значит: ${detail.what_it_means}` : null,
    action ? `Поручение: ${action.title}` : null,
    action?.description ?? null,
    action?.deadline_label ? `Срок: ${action.deadline_label}` : null,
    eventUrl ? `Разбор события: ${eventUrl}` : null,
  ];
  return lines.filter(Boolean).join("\n");
}

export function MailtoPanel({ detail }: { detail: FeedItemDetail }) {
  const [open, setOpen] = useState(false);
  const [actionId, setActionId] = useState("");
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const toParsed = parseRecipients(to);
  const ccParsed = parseRecipients(cc);

  const mailto = useMemo(() => {
    const params = new URLSearchParams();
    if (subject.trim()) params.set("subject", subject.trim());
    if (body.trim()) params.set("body", body.trim());
    const ccEmails = parseRecipients(cc).valid;
    if (ccEmails.length > 0) params.set("cc", ccEmails.join(","));
    const query = params.toString();
    return `mailto:${parseRecipients(to).valid.join(",")}${query ? `?${query}` : ""}`;
  }, [body, cc, subject, to]);

  const openComposer = () => {
    setOpen(true);
    setError(null);
    if (!subject.trim()) setSubject(defaultSubject(detail, actionId));
    if (!body.trim()) setBody(defaultBody(detail, actionId));
  };

  const selectAction = (value: string) => {
    setActionId(value);
    setSubject(defaultSubject(detail, value));
    setBody(defaultBody(detail, value));
    setError(null);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (toParsed.valid.length === 0) {
      setError("Укажите хотя бы одного получателя");
      return;
    }
    if (toParsed.invalid.length > 0) {
      setError(`Проверьте адрес: ${toParsed.invalid.join(", ")}`);
      return;
    }
    if (ccParsed.invalid.length > 0) {
      setError(`Проверьте копию: ${ccParsed.invalid.join(", ")}`);
      return;
    }
    if (!subject.trim()) {
      setError("Укажите тему письма");
      return;
    }
    if (!body.trim()) {
      setError("Добавьте текст поручения");
      return;
    }
    window.location.href = mailto;
  };

  return (
    <section className="event-section event-mailto">
      <SectionHeader title="Поручения по почте" tight />

      {!open ? (
        <div className="event-mailto__card">
          <p className="event-mailto__title">Отправьте поручение из разбора</p>
          <p className="event-mailto__note">
            Соберите письмо и откройте его в Outlook или почтовом клиенте по умолчанию.
            Отправку подтвердите там — приложение не отправляет письма само.
          </p>
          <div className="event-mailto__actions">
            <button
              type="button"
              className="event-mailto__button event-mailto__button--primary"
              onClick={openComposer}
            >
              Собрать письмо
            </button>
          </div>
        </div>
      ) : (
        <form className="event-mailto__card event-mailto__form" onSubmit={submit}>
          <label className="event-mailto__field">
            <span>Поручение из разбора</span>
            <select value={actionId} onChange={(event) => selectAction(event.target.value)}>
              <option value="">Своё поручение</option>
              {detail.actions.map((action, index) => (
                <option key={actionKey(action, index)} value={actionKey(action, index)}>
                  {action.title}
                </option>
              ))}
            </select>
          </label>

          <label className="event-mailto__field">
            <span>Кому</span>
            <input
              value={to}
              onChange={(event) => setTo(event.target.value)}
              placeholder="colleague@company.ru, manager@company.ru"
            />
          </label>

          <label className="event-mailto__field">
            <span>Копия</span>
            <input
              value={cc}
              onChange={(event) => setCc(event.target.value)}
              placeholder="Необязательно"
            />
          </label>

          <label className="event-mailto__field">
            <span>Тема</span>
            <input
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              placeholder="Поручение по событию"
            />
          </label>

          <label className="event-mailto__field">
            <span>Текст</span>
            <textarea value={body} onChange={(event) => setBody(event.target.value)} rows={8} />
          </label>

          {error ? <p className="event-mailto__error">{error}</p> : null}

          <div className="event-mailto__actions">
            <button
              type="submit"
              className="event-mailto__button event-mailto__button--primary"
            >
              Открыть в почте
            </button>
            <button
              type="button"
              className="event-mailto__button event-mailto__button--ghost"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
            >
              Отмена
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
