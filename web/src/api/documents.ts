import { awaitable, parse } from "./client";
import type { Document } from "./types";

export function listDocuments(spaceId: string) {
  return parse<Document[]>(awaitable(`/api/spaces/${spaceId}/documents`));
}

export function uploadDocument(spaceId: string, file: File) {
  const body = new FormData();
  body.append("file", file);
  return parse<Document>(awaitable(`/api/spaces/${spaceId}/documents`, { method: "POST", body }));
}

export function replaceDocument(spaceId: string, docId: string, file: File) {
  const body = new FormData();
  body.append("file", file);
  return parse<Document>(
    awaitable(`/api/spaces/${spaceId}/documents/${docId}`, { method: "PUT", body }),
  );
}

export function deleteDocument(spaceId: string, docId: string) {
  return parse<{ ok: boolean }>(
    awaitable(`/api/spaces/${spaceId}/documents/${docId}`, { method: "DELETE" }),
  );
}

export function splitPageAnchor(filePath: string): { filename: string; page?: number } {
  const m = /^(.*)#page=(\d+)$/.exec(filePath);
  if (!m) return { filename: filePath };
  const page = Number(m[2]);
  if (page < 1) return { filename: filePath };
  return { filename: m[1], page };
}

export function originalUrl(spaceId: string, docId: string, page?: number): string {
  const url = `/api/spaces/${spaceId}/documents/${docId}/original`;
  if (page && page > 0) return url + "#page=" + page;
  return url;
}

export function openOriginal(spaceId: string, docId: string, page?: number): void {
  // 同源打开原文件（不是 MinerU 解析稿）。PDF 可用 #page=n 落到页。
  window.open(originalUrl(spaceId, docId, page), "_blank", "noopener");
}
