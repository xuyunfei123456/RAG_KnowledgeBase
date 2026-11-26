import { FormEvent, useEffect, useState } from "react";
import * as api from "../api";

export function Workbench({
  account,
  onLogout,
}: {
  account: api.Account;
  onLogout: () => void;
}) {
  const [spaces, setSpaces] = useState<api.Space[]>([]);
  const [current, setCurrent] = useState<api.Space | null>(null);
  const [spaceName, setSpaceName] = useState("");
  const [newUser, setNewUser] = useState("");
  const [newPass, setNewPass] = useState("");
  const [message, setMessage] = useState("");
  const [showAccount, setShowAccount] = useState(false);

  async function reload() {
    const list = await api.listSpaces();
    setSpaces(list);
    setCurrent((prev) => list.find((s) => s.id === prev?.id) ?? list[0] ?? null);
  }

  useEffect(() => {
    reload().catch((err) => setMessage(err instanceof Error ? err.message : "加载失败"));
  }, []);

  async function addSpace(e: FormEvent) {
    e.preventDefault();
    const name = spaceName.trim();
    if (!name) return;
    const space = await api.createSpace(name);
    setSpaceName("");
    setSpaces((xs) => [...xs, space]);
    setCurrent(space);
  }

  async function addAccount(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createAccount(newUser, newPass);
      setNewUser("");
      setNewPass("");
      setMessage("已开通账号 " + newUser);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "开通失败");
    }
  }

  async function logout() {
    await api.logout();
    onLogout();
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
          <button type="button" className="ghost" onClick={logout}>
            退出
          </button>
        </span>
      </header>
      <div className="cols">
        <aside className="col space-col">
          <div className="col-h">知识空间</div>
          <form className="inline" onSubmit={addSpace}>
            <input value={spaceName} onChange={(e) => setSpaceName(e.target.value)} placeholder="新空间名称" />
            <button type="submit" className="primary">
              创建
            </button>
          </form>
          <ul className="list">
            {spaces.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  className={s.id === current?.id ? "row active" : "row"}
                  onClick={() => setCurrent(s)}
                >
                  {s.name}
                </button>
              </li>
            ))}
          </ul>
          {spaces.length === 0 ? <p className="empty">还没有知识空间</p> : null}
        </aside>
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
        <aside className="col">
          <div className="col-h">文档</div>
          <p className="empty">下一批次：上传 PDF / Word / Markdown</p>
        </aside>
      </div>
      {showAccount ? (
        <div className="drawer">
          <h2>开通账号</h2>
          <form onSubmit={addAccount}>
            <label>
              用户名
              <input value={newUser} onChange={(e) => setNewUser(e.target.value)} />
            </label>
            <label>
              密码
              <input type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} />
            </label>
            <button type="submit" className="primary">
              开通
            </button>
          </form>
          {message ? <p className="hint">{message}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
