// Error thrown by the API client (real backend or demo data). `detail` carries the backend's message.
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// Detail used when a flight isn't part of the recorded demo data.
export const NOT_IN_DEMO = "not_in_demo";
