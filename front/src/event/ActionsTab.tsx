import type { FeedItemDetail } from "../api";
import { SectionHeader } from "./SectionHeader";

type ActionsTabProps = {
  detail: FeedItemDetail;
};

function labelOrigin(origin: string): string {
  return origin.toLowerCase() === "ai" ? "Вывод AI" : origin;
}


export function ActionsTab({ detail }: ActionsTabProps) {
  const primaryIndex = detail.actions.findIndex((action) => action.is_primary);
  const heroIndex = primaryIndex >= 0 ? primaryIndex : 0;
  const hero = detail.actions[heroIndex];
  const rest = detail.actions.filter((_, index) => index !== heroIndex);
  const product = detail.product;

  return (
    <>
      <section className="event-section">
        <SectionHeader title="Что сделать" tight />

        {hero ? (
          <>
            <article className="event-action-hero">
              <p className="event-action-hero__title">{hero.title}</p>
              {hero.description ? (
                <p className="event-action-hero__text">{hero.description}</p>
              ) : null}
              {hero.deadline_label || hero.deadline ? (
                <p className="event-action-hero__text">
                  Срок: {hero.deadline_label ?? hero.deadline}
                </p>
              ) : null}
              <p className="event-action-hero__source">
                {[hero.role, labelOrigin(hero.origin)].filter(Boolean).join(" · ")}
              </p>
            </article>

            {rest.length > 0 ? (
              <div className="event-actions__pair">
                {rest.map((action, index) => (
                  <article
                    key={action.id ?? `${action.title}-${index}`}
                    className="event-action-card"
                  >
                    <p className="event-action-card__title">{action.title}</p>
                    {action.description ? (
                      <p className="event-action-card__text">{action.description}</p>
                    ) : null}
                    {action.deadline_label || action.deadline ? (
                      <p className="event-action-card__text">
                        Срок: {action.deadline_label ?? action.deadline}
                      </p>
                    ) : null}
                    <p className="event-action-card__source">
                      {[action.role, labelOrigin(action.origin)].filter(Boolean).join(" · ")}
                    </p>
                  </article>
                ))}
              </div>
            ) : null}
          </>
        ) : (
          <p className="event-stub">Пока нет данных по этому разделу</p>
        )}
      </section>

      {detail.checklist.length > 0 ? (
        <section className="event-section">
          <SectionHeader title="Проверить дополнительно" tight />
          <div className="event-checklist">
            <span className="event-checklist__accent" aria-hidden="true" />
            <div className="event-checklist__items">
              {detail.checklist.map((item) => (
                <p key={item} className="event-checklist__item">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {product ? (
        <section className="event-section">
          <article className="event-product">
            <p className="event-product__eyebrow">Продукт Альфа-Банка</p>
            <p className="event-product__title">{product.name}</p>
            <p className="event-product__text">{product.description}</p>
            {product.benefit ? <p className="event-product__text">{product.benefit}</p> : null}
          </article>
        </section>
      ) : null}
    </>
  );
}
