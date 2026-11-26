import { FormEvent, useState } from "react";
import * as api from "../api";

export function LoginPage({ onLogin }: { onLogin: (a: api.Account) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (pending) return;
    setError("");
    setPending(true);
    try {
      onLogin(await api.login(username, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
      setPending(false);
    }
  }

  return (
    <div className="login-shell">
      <header className="topbar">
        <span className="brand">知识库</span>
      </header>
      <form className="login-card" onSubmit={submit}>
        <h1>登录</h1>
        <label>
          用户名
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            disabled={pending}
          />
        </label>
        <label>
          密码
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            disabled={pending}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" className="primary" disabled={pending}>
          {pending ? "登录中" : "登录"}
        </button>
        <p className="hint">没有注册。账号由引导账号开通。</p>
      </form>
    </div>
  );
}
