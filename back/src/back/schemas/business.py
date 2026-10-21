from pydantic import BaseModel

from back.schemas.common import ORMModel


class BusinessListItem(ORMModel):
    uid: str
    org_type: str | None = None
    eco_mark_label: str | None = None
    main_okved_code: str | None = None
    main_okved_name: str | None = None
    amount_workers_fns_gradation: str | None = None
    revenue: float | None = None
    revenue_segment: str
    city: str | None = None
    region: str | None = None
    fts_country_name: str | None = None
    cl_product_rko_mark: bool = False
    cl_product_loa_mark: bool = False
    tags: list[str] = []


class BusinessOut(BusinessListItem):
    okfs_name: str | None = None
    company_age_years_gradation: str | None = None
    negative_mark: float | None = None
    amount_workers_spark_gradation: str | None = None
    client_type: str | None = None
    cl_product_gar_mark: bool = False
    cl_product_lea_mark: bool = False
    cl_product_dep_mark: bool = False
    cl_product_zpp_mark: bool = False
    fts_flag: bool = False
    factoring_mark: bool = False
    group_id: str | None = None


class BusinessOptionsResponse(BaseModel):
    mode: str
    items: list[BusinessListItem]
    total: int


class BusinessSelectRequest(BaseModel):
    uid: str
