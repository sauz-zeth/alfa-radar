export function cleanInfluenceText(value: string, maxLength = 140): string {
  const text = value
    .replace(/<!--.*?-->/gs, " ")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*(?:---+|___+|\*\*\*+)\s*$/gm, " ")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*_~`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const sentence = text.match(/^.*?[.!?](?=\s|$)/)?.[0] ?? text;
  return sentence.length > maxLength ? `${sentence.slice(0, maxLength - 1).trimEnd()}…` : sentence;
}

type EffectChainInput = {
  title: string;
  factor: string | null;
  whatItMeans: string;
  consequence: string | null;
  impactLabel: string;
};

export function buildEffectChain(input: EffectChainInput) {
  return [
    { label: "Событие", value: cleanInfluenceText(input.title), note: "" },
    { label: "Фактор", value: cleanInfluenceText(input.factor || input.whatItMeans), note: "" },
    {
      label: "Последствие",
      value: cleanInfluenceText(
        input.consequence || `${input.impactLabel} для профиля бизнеса`,
      ),
      note: input.consequence ? "Вывод AI" : "",
    },
  ];
}
