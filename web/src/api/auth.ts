import { awaitable, parse } from "./client";
import type { Account } from "./types";

export function login(username: string, password: string) {
  return parse<Account>(
    awaitable("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  );
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
