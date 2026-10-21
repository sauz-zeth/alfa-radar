"""Curated companies for the onboarding dropdown.

They are picked from different OKVED groups and revenue segments so that the
first screen shows a representative sample instead of 85k rows. The dropdown
can still search the full company table.
"""

FEATURED_COMPANY_UIDS: tuple[str, ...] = (
    "U_57706",  # оптовая торговля топливом
    "U_9250",  # строительство инженерных сооружений
    "U_8318",  # автобизнес, оптовая торговля автозапчастями
    "U_3263",  # грузовые перевозки
    "U_4909",  # производство электроэнергии
    "U_401523",  # финансовые услуги
    "U_212593",  # рестораны и кафе
    "U_88715",  # производство электрооборудования
    "U_49201",  # рекламные агентства
    "U_19717",  # розничная торговля моторным топливом
    "U_44792",  # разработка ПО
    "U_16802",  # производство спецодежды
    "U_257705",  # производство лекарств
    "U_408981",  # добыча нефти
    "U_204078",  # производство сыра и пищевых продуктов
)
