import { ChangeEvent, useEffect, useRef, useState } from "react";
import * as api from "../../api";
import type { Document, Space } from "../../api";

function statusLabel(status: api.DocStatus): string {
  if (status === "processing") return "处理中";
  if (status === "ready") return "已就绪";
  return "失败";
}

function allowedFile(name: string): boolean {
  return /\.(pdf|docx|md|markdown)$/i.test(name);
}

export function Documents({
  space,
  onDocumentsChanged,
}: {
  space: Space | null;
  onDocumentsChanged: () => void;
}) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState("");
  const [replacingId, setReplacingId] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const replaceInput = useRef<HTMLInputElement>(null);
  const replaceTarget = useRef("");

  const processing = docs.some((d) => d.status === "processing");
  const busy = uploading || Boolean(deletingId) || Boolean(replacingId);

  useEffect(() => {
    if (!space) {
      setDocs([]);
      setError("");
      return;
    }
    let cancelled = false;
    const spaceId = space.id;
    api
      .listDocuments(spaceId)
      .then((list) => {
        if (!cancelled) setDocs(list);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "加载文档失败");
      });
    return () => {
      cancelled = true;
    };
  }, [space?.id]);

  useEffect(() => {
    if (!space || !processing) return;
    const spaceId = space.id;
    const timer = window.setInterval(() => {
      api.listDocuments(spaceId).then(setDocs).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [space?.id, processing]);

  async function onUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !space || busy) return;
    if (!allowedFile(file.name)) {
      setError("只接受 PDF、Word、Markdown");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const doc = await api.uploadDocument(space.id, file);
      setDocs((xs) => [doc, ...xs]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  function onReplaceClick(doc: Document) {
    if (!space || busy || doc.status === "processing") return;
    replaceTarget.current = doc.id;
    replaceInput.current?.click();
  }

  async function onReplace(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    const docId = replaceTarget.current;
    replaceTarget.current = "";
    if (!file || !space || !docId || busy) return;
    if (!allowedFile(file.name)) {
      setError("只接受 PDF、Word、Markdown");
      return;
    }
    setReplacingId(docId);
    setError("");
    try {
      const next = await api.replaceDocument(space.id, docId, file);
      setDocs((xs) => xs.map((d) => (d.id === next.id ? next : d)));
      onDocumentsChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "替换失败");
    } finally {
      setReplacingId("");
    }
  }

  async function onDelete(doc: Document) {
    if (!space || busy || doc.status === "processing") return;
    if (!window.confirm("确定删除「" + doc.filename + "」？")) return;
    setDeletingId(doc.id);
    setError("");
    try {
      await api.deleteDocument(space.id, doc.id);
      setDocs((xs) => xs.filter((d) => d.id !== doc.id));
      onDocumentsChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeletingId("");
    }
  }

  function onOpen(doc: Document) {
    if (!space) return;
    api.openOriginal(space.id, doc.id);
  }

  return (
    <aside className="col">
      <div className="col-h">文档</div>
      {space ? (
        <>
          <div className="inline">
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.docx,.md,.markdown"
              hidden
              onChange={onUpload}
            />
            <input
              ref={replaceInput}
              type="file"
              accept=".pdf,.docx,.md,.markdown"
              hidden
              onChange={onReplace}
            />
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => fileInput.current?.click()}
            >
              {uploading ? "上传中" : "上传"}
            </button>
          </div>
          {error ? <p className="error doc-err">{error}</p> : null}
          <ul className="list">
            {docs.map((d) => (
              <li key={d.id} className="doc-item">
                <div className="doc-name">{d.filename}</div>
                {d.status === "failed" && d.error_msg ? <p className="error doc-err">{d.error_msg}</p> : null}
                <div className="doc-meta">
                  <span className={"doc-st " + d.status}>{statusLabel(d.status)}</span>
                  <button type="button" className="ghost" onClick={() => onOpen(d)}>
                    打开原文
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy || d.status === "processing"}
                    onClick={() => onReplaceClick(d)}
                  >
                    {replacingId === d.id ? "替换中" : "替换"}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy || d.status === "processing"}
                    onClick={() => onDelete(d)}
                  >
                    {deletingId === d.id ? "删除中" : "删除"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {docs.length === 0 ? <p className="empty">还没有文档</p> : null}
        </>
      ) : (
        <p className="empty">先创建一个知识空间</p>
      )}
    </aside>
  );
}
