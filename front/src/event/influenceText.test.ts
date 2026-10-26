import { describe, expect, it } from "bun:test";
import { buildEffectChain, cleanInfluenceText } from "./influenceText";

describe("cleanInfluenceText", () => {
  it("removes markdown structure and page markers", () => {
    expect(cleanInfluenceText("#### Долговой рынок\n<!-- конец стр. 1 -->\n---\nТекст."))
      .toBe("Долговой рынок Текст.");
  });

  it("keeps only the first sentence and caps long text", () => {
    expect(cleanInfluenceText("Силы ПВО отражают атаку. Длинное продолжение новости."))
      .toBe("Силы ПВО отражают атаку.");
    expect(cleanInfluenceText("А".repeat(180))).toHaveLength(141);
  });
});

describe("buildEffectChain", () => {
  it("uses profile meaning instead of the generic backend placeholder", () => {
    const chain = buildEffectChain({
      title: "Атака БПЛА на промышленный узел",
      factor: null,
      whatItMeans: "Логистика поставок может замедлиться.",
      consequence: null,
      impactLabel: "Риск",
    });

    expect(chain.map((step) => step.value)).toEqual([
      "Атака БПЛА на промышленный узел",
      "Логистика поставок может замедлиться.",
      "Риск для профиля бизнеса",
    ]);
  });

  it("prefers the calculated metric as the consequence", () => {
    const chain = buildEffectChain({
      title: "Пошлина",
      factor: "7% Ставка пошлины",
      whatItMeans: "Маржа снизится.",
      consequence: "−1,2 млрд ₽ EBITDA в год",
      impactLabel: "Риск",
    });

    expect(chain[1]?.value).toBe("7% Ставка пошлины");
    expect(chain[2]).toMatchObject({ value: "−1,2 млрд ₽ EBITDA в год", note: "Вывод AI" });
  });
});
