export type Account = { id: string; username: string };
export type Space = { id: string; name: string; lightrag_workspace: string };

async function parse<T>(res: Response | Promise<Response>): Promise<T> {
  const r = await res;
  if (r.status === 401) {
    throw new Error("未登录");
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? "请求失败");
  }
  return r.json() as Promise<T>;
}

export function login(username: string, password: string) {
  return parse<Account>(
    awaitable("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  );
}

function awaitable(url: string, init?: RequestInit) {
  return fetch(url, { credentials: "include", ...init });
}

export function logout() {
  return parse<{ ok: boolean }>(awaitable("/api/auth/logout", { method: "POST" }));
}

export function me() {
  return parse<Account>(awaitable("/api/auth/me"));
}

export function createAccount(username: string, password: string) {
  return parse<Account>(
    awaitable("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  );
}

export function listSpaces() {
  return parse<Space[]>(awaitable("/api/spaces"));
}

export function createSpace(name: string) {
  return parse<Space>(
    awaitable("/api/spaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  );
}
