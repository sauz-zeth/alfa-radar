from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    CEO = "ceo"
    CFO = "cfo"
    CHIEF_ACCOUNTANT = "chief_accountant"
    TREASURER = "treasurer"
    C_LEVEL = "c_level"
    OTHER_DECISION_MAKER = "other_decision_maker"


ROLE_LABELS: dict[Role, str] = {
    Role.OWNER: "Собственник бизнеса",
    Role.CEO: "Генеральный директор",
    Role.CFO: "Финансовый директор",
    Role.CHIEF_ACCOUNTANT: "Главный бухгалтер",
    Role.TREASURER: "Руководитель казначейства",
    Role.C_LEVEL: "Другой C-level-руководитель",
    Role.OTHER_DECISION_MAKER: (
        "Иной сотрудник, влияющий на принятие решений и имеющий доступ к интернет-банку"
    ),
}


class Impact(StrEnum):
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    MIXED = "mixed"
    NEUTRAL = "neutral"


IMPACT_LABELS: dict[Impact, str] = {
    Impact.RISK: "Риск",
    Impact.OPPORTUNITY: "Возможность",
    Impact.MIXED: "Смешанное риск/возможность",
    Impact.NEUTRAL: "Нейтрально",
}


class CounterpartyDirection(StrEnum):
    SUPPLIER = "supplier"
    BUYER = "buyer"


class ReportingForm(StrEnum):
    BALANCE = "balance"
    INCOME = "income"
    CASH_FLOW = "cash_flow"


REPORTING_FORM_LABELS: dict[ReportingForm, str] = {
    ReportingForm.BALANCE: "Бухгалтерский баланс",
    ReportingForm.INCOME: "Отчёт о финансовых результатах",
    ReportingForm.CASH_FLOW: "Отчёт о движении денежных средств",
}


class OnboardingStep(StrEnum):
    REGISTERED = "registered"
    BUSINESS_SELECTED = "business_selected"
    PROFILE_FILLED = "profile_filled"
    ROLE_SELECTED = "role_selected"
    COUNTERPARTIES_CONFIGURED = "counterparties_configured"
    CATEGORIES_CONFIGURED = "categories_configured"
    REPORTING_UPLOADED = "reporting_uploaded"
    COMPLETED = "completed"


ONBOARDING_ORDER: tuple[OnboardingStep, ...] = (
    OnboardingStep.REGISTERED,
    OnboardingStep.BUSINESS_SELECTED,
    OnboardingStep.PROFILE_FILLED,
    OnboardingStep.ROLE_SELECTED,
    OnboardingStep.COUNTERPARTIES_CONFIGURED,
    OnboardingStep.CATEGORIES_CONFIGURED,
    OnboardingStep.REPORTING_UPLOADED,
    OnboardingStep.COMPLETED,
)

PROGNOSIS_NOTE = "При детальном разборе во вкладке «Отслеживаемое» прогноз может уточниться"

DEFAULT_ENTREPRENEUR_NAME = "Иван Иванов"
DEFAULT_BUSINESS_NAME = "Моя компания"
