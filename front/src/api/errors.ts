export interface ApiErrorInit {
  status: number;
  detail: string;
  url: string;
  payload?: unknown;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly url: string;
  readonly payload: unknown;

  constructor({ status, detail, url, payload }: ApiErrorInit) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.url = url;
    this.payload = payload;
  }
}
