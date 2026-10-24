import { useMemo, useState } from "react";
import {
  ApiError,
  useApi,
  useApiMutation,
  useApiQuery,
  useQueryClient,
  type FeedItemDetail,
  type OutlookImportance,
  type OutlookMessage,
  type OutlookRecipient,
  type OutlookState,
} from "../api";
import { SectionHeader } from "./SectionHeader";
import "./event-outlook.css";

const ADVANCE_LABELS: Record<string, string> = {
  sent: "Доставлено",
  delivered: "Прочитано",
  read: "Ответ получен",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  sent: "Отправлено",
  delivered: "Доставлено",
  read: "Прочитано",
  replied: "Ответ получен",
};

function errorText(error: Error | null): string | null {
  if (!error) return null;
  if (error instanceof ApiError) return error.detail;
  return error.message || "Не удалось выполнить действие";
}

function parseRecipients(value: string): OutlookRecipient[] {
  return value
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const match = item.match(/^(.+?)\s*<([^>]+)>$/);
      if (match) return { name: match[1]?.trim() ?? "", email: match[2]?.trim() ?? "" };
      return { name: "", email: item };
    });
}

function actionKey(action: FeedItemDetail["actions"][number], index: number): string {
  return action.id ?? `action-${index}`;
}

function defaultBody(detail: FeedItemDetail, actionId: string): string {
  const index = detail.actions.findIndex((item, position) => actionKey(item, position) === actionId);
  const action = index >= 0 ? detail.actions[index] : undefined;
  const lines = [
    "Здравствуйте!",
    "",
    `По событию «${detail.title}».`,
    detail.what_it_means ? `Что это значит: ${detail.what_it_means}` : null,
    action ? `Поручение: ${action.title}` : null,
    action?.description ?? null,
    action?.deadline_label ? `Срок: ${action.deadline_label}` : null,
    "",
    "Разбор события и оценка влияния приложены.",
  ];
  return lines.filter(Boolean).join("\n");
}

function formatDue(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
  }).format(date);
}

function recipientsLabel(message: OutlookMessage): string {
  return message.to
    .map((item) => item.name || item.email)
    .filter(Boolean)
    .join(", ");
}

export function OutlookPanel({ detail }: { detail: FeedItemDetail }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [connectEmail, setConnectEmail] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [actionId, setActionId] = useState("");
  const [to, setTo] = useState("");
  const [cc, setCc] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [due, setDue] = useState("");
  const [importance, setImportance] = useState<OutlookImportance>("normal");
  const [formError, setFormError] = useState<string | null>(null);

  const stateQuery = useApiQuery({
    queryKey: ["outlook", detail.id],
    queryFn: (signal) => api.outlook.state({ event_id: detail.id }, { signal }),
  });

  const contactsQuery = useApiQuery({
    queryKey: ["outlook", "contacts"],
    queryFn: (signal) => api.outlook.contacts({}, { signal }),
    staleTime: 60_000,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["outlook"] });
  };

  const connect = useApiMutation<OutlookState, string>({
    mutationFn: (email) => api.outlook.connect({ email }),
    onSuccess: () => {
      setConnectEmail("");
      invalidate();
    },
  });

  const disconnect = useApiMutation<OutlookState, void>({
    mutationFn: () => api.outlook.disconnect(),
    onSuccess: invalidate,
  });

  const createMessage = useApiMutation<OutlookMessage, boolean>({
    mutationFn: (sendNow) =>
      api.outlook.createMessage({
        event_id: detail.id,
        action_id: actionId || null,
        to: parseRecipients(to),
        cc: parseRecipients(cc),
        subject: subject.trim(),
        body: body.trim(),
        importance,
        due_at: due || null,
        attach_report: true,
        send_now: sendNow,
      }),
    onSuccess: () => {
      setComposerOpen(false);
      setActionId("");
      setTo("");
      setCc("");
      setSubject("");
      setBody("");
      setDue("");
      setImportance("normal");
      setFormError(null);
      invalidate();
    },
  });

  const send = useApiMutation<OutlookMessage, string>({
    mutationFn: (messageId) => api.outlook.send(messageId),
    onSuccess: invalidate,
  });

  const remind = useApiMutation<OutlookMessage, string>({
    mutationFn: (messageId) => api.outlook.remind(messageId),
    onSuccess: invalidate,
  });

  const advance = useApiMutation<OutlookMessage, string>({
    mutationFn: (messageId) => api.outlook.advance(messageId),
    onSuccess: invalidate,
  });

  const remove = useApiMutation<void, string>({
    mutationFn: (messageId) => api.outlook.deleteMessage(messageId),
    onSuccess: invalidate,
  });

  const state = stateQuery.data;
  const contacts = contactsQuery.data?.items ?? [];
  const messages = state?.messages ?? [];
  const busy =
    send.isPending || remind.isPending || advance.isPending || remove.isPending;

  const error =
    errorText(connect.error) ??
    errorText(disconnect.error) ??
    errorText(createMessage.error) ??
    errorText(send.error) ??
    errorText(remind.error) ??
    errorText(advance.error) ??
    errorText(remove.error) ??
    formError;

  const mailto = useMemo(() => {
    const recipients = parseRecipients(to).map((item) => item.email).join(",");
    const copy = parseRecipients(cc).map((item) => item.email).join(",");
    const params = new URLSearchParams();
    if (subject.trim()) params.set("subject", subject.trim());
    if (body.trim()) params.set("body", body.trim());
    if (copy) params.set("cc", copy);
    const query = params.toString();
    return `mailto:${recipients}${query ? `?${query}` : ""}`;
  }, [body, cc, subject, to]);

  const selectAction = (value: string) => {
    setActionId(value);
    if (!value) {
      setSubject("");
      setBody("");
      return;
    }
    const index = detail.actions.findIndex((item, position) => actionKey(item, position) === value);
    const action = index >= 0 ? detail.actions[index] : undefined;
    setSubject(action ? `Поручение: ${action.title}` : `Поручение: ${detail.title}`);
    setBody(defaultBody(detail, value));
  };

  const addContact = (email: string) => {
    setTo((current) => {
      const items = parseRecipients(current);
      if (items.some((item) => item.email === email)) return current;
      return [...items.map((item) => item.email), email].join(", ");
    });
  };

  const submit = (sendNow: boolean) => {
    setFormError(null);
    if (parseRecipients(to).length === 0) {
      setFormError("Укажите хотя бы одного получателя");
      return;
    }
    if (!subject.trim()) {
      setFormError("Укажите тему письма");
      return;
    }
    if (!body.trim()) {
      setFormError("Добавьте текст поручения");
      return;
    }
    createMessage.mutate(sendNow);
  };

  if (stateQuery.isPending) {
    return (
      <section className="event-section event-outlook">
        <SectionHeader title="Поручения через Outlook" tight />
        <p className="event-outlook__note">Загружаем подключение…</p>
      </section>
    );
  }

  if (stateQuery.isError || !state) {
    return (
      <section className="event-section event-outlook">
        <SectionHeader title="Поручения через Outlook" tight />
        <div className="event-outlook__card">
          <p className="event-outlook__note">
            {errorText(stateQuery.error) ?? "Не удалось загрузить Outlook"}
          </p>
          <button
            type="button"
            className="event-outlook__button"
            onClick={() => stateQuery.refetch()}
          >
            Повторить
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="event-section event-outlook">
      <SectionHeader title="Поручения через Outlook" tight />

      {!state.connected ? (
        <div className="event-outlook__card">
          <p className="event-outlook__title">Отправляйте поручения коллегам из разбора</p>
          <p className="event-outlook__note">
            Подключите Outlook, чтобы создавать черновики и отправлять письма со сроком и
            вложением. В демо-режиме письма не уходят в Microsoft 365.
          </p>
          <form
            className="event-outlook__connect"
            onSubmit={(event) => {
              event.preventDefault();
              if (connectEmail.trim()) connect.mutate(connectEmail.trim());
            }}
          >
            <input
              type="email"
              value={connectEmail}
              onChange={(event) => setConnectEmail(event.target.value)}
              placeholder="owner@company.example"
              aria-label="Почта Outlook"
              required
            />
            <button
              type="submit"
              className="event-outlook__button event-outlook__button--primary"
              disabled={connect.isPending}
            >
              {connect.isPending ? "Подключаем…" : "Подключить Outlook"}
            </button>
          </form>
        </div>
      ) : (
        <>
          <div className="event-outlook__card event-outlook__account">
            <div>
              <p className="event-outlook__title">{state.email}</p>
              <p className="event-outlook__note">
                Outlook подключён · права: {state.scopes.join(", ")}
              </p>
            </div>
            <div className="event-outlook__account-actions">
              <button
                type="button"
                className="event-outlook__button event-outlook__button--primary"
                onClick={() => setComposerOpen((value) => !value)}
              >
                {composerOpen ? "Свернуть" : "Новое поручение"}
              </button>
              <button
                type="button"
                className="event-outlook__button"
                onClick={() => disconnect.mutate()}
                disabled={disconnect.isPending}
              >
                Отключить
              </button>
            </div>
          </div>

          {composerOpen ? (
            <form
              className="event-outlook__card event-outlook__form"
              onSubmit={(event) => {
                event.preventDefault();
                submit(false);
              }}
            >
              <label className="event-outlook__field">
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

              <label className="event-outlook__field">
                <span>Кому</span>
                <input
                  value={to}
                  onChange={(event) => setTo(event.target.value)}
                  placeholder="cfo@company.example"
                />
              </label>
              {contacts.length > 0 ? (
                <div className="event-outlook__chips" aria-label="Подсказки из адресной книги">
                  {contacts.slice(0, 6).map((contact) => (
                    <button
                      key={`${contact.source}-${contact.email}`}
                      type="button"
                      className="event-outlook__chip"
                      onClick={() => addContact(contact.email)}
                    >
                      {contact.name} · {contact.role}
                    </button>
                  ))}
                </div>
              ) : null}

              <label className="event-outlook__field">
                <span>Копия</span>
                <input
                  value={cc}
                  onChange={(event) => setCc(event.target.value)}
                  placeholder="Необязательно"
                />
              </label>

              <label className="event-outlook__field">
                <span>Тема</span>
                <input
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                  placeholder="Поручение по событию"
                />
              </label>

              <label className="event-outlook__field">
                <span>Текст</span>
                <textarea
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  rows={7}
                />
              </label>

              <div className="event-outlook__row">
                <label className="event-outlook__field">
                  <span>Срок</span>
                  <input
                    type="date"
                    value={due}
                    onChange={(event) => setDue(event.target.value)}
                  />
                </label>
                <label className="event-outlook__field">
                  <span>Важность</span>
                  <select
                    value={importance}
                    onChange={(event) =>
                      setImportance(event.target.value === "high" ? "high" : "normal")
                    }
                  >
                    <option value="normal">Обычная</option>
                    <option value="high">Высокая · к исполнению</option>
                  </select>
                </label>
              </div>

              <p className="event-outlook__note">
                К письму будет приложен PDF разбора. В демо-режиме вложение и статусы
                моделируются.
              </p>

              {error ? <p className="event-outlook__error">{error}</p> : null}

              <div className="event-outlook__actions">
                <button
                  type="submit"
                  className="event-outlook__button event-outlook__button--primary"
                  disabled={createMessage.isPending}
                >
                  {createMessage.isPending ? "Сохраняем…" : "Сохранить черновик"}
                </button>
                <button
                  type="button"
                  className="event-outlook__button"
                  onClick={() => submit(true)}
                  disabled={createMessage.isPending}
                >
                  Отправить
                </button>
                <a className="event-outlook__button" href={mailto}>
                  Открыть в Outlook
                </a>
                <button
                  type="button"
                  className="event-outlook__button event-outlook__button--ghost"
                  onClick={() => setComposerOpen(false)}
                >
                  Отмена
                </button>
              </div>
            </form>
          ) : null}

          {error && !composerOpen ? <p className="event-outlook__error">{error}</p> : null}

          <div className="event-outlook__messages">
            {messages.length === 0 ? (
              <p className="event-outlook__note">По этому событию поручений пока нет.</p>
            ) : (
              messages.map((message) => (
                <article key={message.id} className="event-outlook__message">
                  <div className="event-outlook__message-head">
                    <span
                      className={`event-outlook__status event-outlook__status--${message.status}`}
                    >
                      {STATUS_LABELS[message.status] ?? message.status_label}
                    </span>
                    {message.importance === "high" ? (
                      <span className="event-outlook__flag">К исполнению</span>
                    ) : null}
                    {message.attachment_name ? (
                      <span className="event-outlook__attachment">PDF разбора</span>
                    ) : null}
                  </div>

                  <p className="event-outlook__message-title">{message.subject}</p>
                  <p className="event-outlook__note">
                    Кому: {recipientsLabel(message)}
                    {message.due_at ? ` · срок: ${formatDue(message.due_at)}` : ""}
                  </p>
                  {message.reminder_count > 0 ? (
                    <p className="event-outlook__note">
                      Напоминаний отправлено: {message.reminder_count}
                    </p>
                  ) : null}

                  <div className="event-outlook__actions">
                    {message.status === "draft" ? (
                      <>
                        <button
                          type="button"
                          className="event-outlook__button event-outlook__button--primary"
                          onClick={() => send.mutate(message.id)}
                          disabled={busy}
                        >
                          Отправить
                        </button>
                        <button
                          type="button"
                          className="event-outlook__button event-outlook__button--ghost"
                          onClick={() => remove.mutate(message.id)}
                          disabled={busy}
                        >
                          Удалить
                        </button>
                      </>
                    ) : null}

                    {ADVANCE_LABELS[message.status] ? (
                      <button
                        type="button"
                        className="event-outlook__button"
                        onClick={() => advance.mutate(message.id)}
                        disabled={busy}
                      >
                        {ADVANCE_LABELS[message.status]}
                      </button>
                    ) : null}

                    {message.status !== "replied" && message.status !== "draft" ? (
                      <button
                        type="button"
                        className="event-outlook__button event-outlook__button--ghost"
                        onClick={() => remind.mutate(message.id)}
                        disabled={busy}
                      >
                        Напомнить
                      </button>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>

          <p className="event-outlook__note">
            Демо-режим Outlook: подключение, отправка и статусы моделируются. Реальное письмо
            можно открыть в почтовом клиенте кнопкой «Открыть в Outlook».
          </p>
        </>
      )}
    </section>
  );
}
