import { FormEvent, useEffect, useState } from "react";
import * as api from "../../api";
import type { Space } from "../../api";
import { AccountDrawer } from "./AccountDrawer";
import { Documents } from "./Documents";
import { Spaces } from "./Spaces";

export function Workbench({
  account,
  onLogout,
}: {
  account: api.Account;
  onLogout: () => void;
}) {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [current, setCurrent] = useState<Space | null>(null);
  const [spaceName, setSpaceName] = useState("");
  const [spaceError, setSpaceError] = useState("");
  const [showAccount, setShowAccount] = useState(false);
  const [creatingSpace, setCreatingSpace] = useState(false);
  const [deletingSpaceId, setDeletingSpaceId] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);

  async function reload() {
    const list = await api.listSpaces();
    setSpaces(list);
    setCurrent((prev) => list.find((s) => s.id === prev?.id) ?? list[0] ?? null);
  }

  useEffect(() => {
    reload().catch((err) => setSpaceError(err instanceof Error ? err.message : "加载失败"));
  }, []);

  async function addSpace(e: FormEvent) {
    e.preventDefault();
    if (creatingSpace) return;
    const name = spaceName.trim();
    if (!name) return;
    setCreatingSpace(true);
    setSpaceError("");
    try {
      const space = await api.createSpace(name);
      setSpaceName("");
      setSpaces((xs) => [...xs, space]);
      setCurrent(space);
    } catch (err) {
      setSpaceError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreatingSpace(false);
    }
  }

  async function onDeleteSpace(space: Space) {
    if (deletingSpaceId) return;
    if (!window.confirm("确定删除知识空间「" + space.name + "」？该空间下的文档也会被删掉。")) {
      return;
    }
    setDeletingSpaceId(space.id);
    setSpaceError("");
    try {
      await api.deleteSpace(space.id);
      const next = spaces.filter((s) => s.id !== space.id);
      setSpaces(next);
      setCurrent((prev) => (prev?.id === space.id ? (next[0] ?? null) : prev));
    } catch (err) {
      setSpaceError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeletingSpaceId("");
    }
  }

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await api.logout();
      onLogout();
    } catch {
      setLoggingOut(false);
    }
  }

  return (
    <div className="desk">
      <header className="topbar">
        <span className="brand">知识库</span>
        <span className="top-right">
          <button type="button" className="ghost" onClick={() => setShowAccount((v) => !v)}>
            开通账号
          </button>
          <span className="who">{account.username}</span>
          <button type="button" className="ghost" disabled={loggingOut} onClick={logout}>
            {loggingOut ? "退出中" : "退出"}
          </button>
        </span>
      </header>
      <div className="cols">
        <Spaces
          spaces={spaces}
          current={current}
          spaceName={spaceName}
          error={spaceError}
          creating={creatingSpace}
          deletingId={deletingSpaceId}
          onNameChange={setSpaceName}
          onCreate={addSpace}
          onSelect={setCurrent}
          onDelete={onDeleteSpace}
        />
        <aside className="col">
          <div className="col-h">对话</div>
          <p className="empty">下一批次：在当前空间提问</p>
        </aside>
        <main className="col main">
          <div className="col-h">{current ? current.name : "问答"}</div>
          {current ? (
            <p className="meta">当前只检索这个空间（LightRAG workspace：{current.lightrag_workspace}）</p>
          ) : (
            <p className="empty">先创建一个知识空间</p>
          )}
        </main>
        <Documents space={current} />
      </div>
      {showAccount ? <AccountDrawer /> : null}
    </div>
  );
}
