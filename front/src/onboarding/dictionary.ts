import type { Role } from "../api";

export const roles: { value: Role; label: string }[] = [
  { value: "owner", label: "Собственник бизнеса" },
  { value: "ceo", label: "Генеральный директор" },
  { value: "cfo", label: "Финансовый директор" },
  { value: "chief_accountant", label: "Главный бухгалтер" },
  { value: "treasurer", label: "Руководитель казначейства" },
  { value: "c_level", label: "Другой C-level-руководитель" },
  {
    value: "other_decision_maker",
    label: "Иной сотрудник, влияющий на решения и имеющий доступ к интернет-банку",
  },
];

export const directionLabels: Record<string, string> = {
  supplier: "Поставщики",
  buyer: "Покупатели",
};

export const productLabels: Record<string, string> = {
  cl_product_rko_mark: "РКО",
  cl_product_loa_mark: "Кредит",
  cl_product_gar_mark: "Гарантии",
  cl_product_lea_mark: "Лизинг",
  cl_product_dep_mark: "Депозиты",
  cl_product_zpp_mark: "Зарплатный проект",
  factoring_mark: "Факторинг",
};

export const categoryGroups = [
  { key: "direct", label: "Прямое влияние", min: 0.8 },
  { key: "indirect", label: "Косвенное", min: 0.45 },
  { key: "background", label: "Фоновое", min: 0.01 },
] as const;

export function groupCategories<T extends { weight: number }>(items: T[]) {
  return categoryGroups
    .map((group, index) => ({
      ...group,
      items: items.filter((item) => {
        const max = index === 0 ? 1.01 : categoryGroups[index - 1]!.min;
        return item.weight >= group.min && item.weight < max;
      }),
    }))
    .filter((group) => group.items.length > 0);
}
