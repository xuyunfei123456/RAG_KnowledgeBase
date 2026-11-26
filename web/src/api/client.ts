export function errorDetail(body: unknown): string {
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail) return detail;
  return "请求失败";
}

export async function parse<T>(res: Response | Promise<Response>): Promise<T> {
  const r = await res;
  if (r.status === 401) {
    throw new Error("未登录");
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(errorDetail(body));
  }
  return r.json() as Promise<T>;
}

export function awaitable(url: string, init?: RequestInit) {
  return fetch(url, { credentials: "include", ...init });
}
