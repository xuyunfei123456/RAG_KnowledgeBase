import { awaitable, parse } from "./client";
import type { Space } from "./types";

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

export function deleteSpace(spaceId: string) {
  return parse<{ ok: boolean }>(awaitable(`/api/spaces/${spaceId}`, { method: "DELETE" }));
}
