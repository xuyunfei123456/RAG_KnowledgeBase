import { FormEvent, useState } from "react";
import * as api from "../../api";

export function AccountDrawer() {
  const [newUser, setNewUser] = useState("");
  const [newPass, setNewPass] = useState("");
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  async function addAccount(e: FormEvent) {
    e.preventDefault();
    if (creating) return;
    setCreating(true);
    try {
      await api.createAccount(newUser, newPass);
      setMessage("已开通账号 " + newUser);
      setNewUser("");
      setNewPass("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "开通失败");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="drawer">
      <h2>开通账号</h2>
      <form onSubmit={addAccount}>
        <label>
          用户名
          <input value={newUser} onChange={(e) => setNewUser(e.target.value)} disabled={creating} />
        </label>
        <label>
          密码
          <input
            type="password"
            value={newPass}
            onChange={(e) => setNewPass(e.target.value)}
            disabled={creating}
          />
        </label>
        <button type="submit" className="primary" disabled={creating}>
          {creating ? "开通中" : "开通"}
        </button>
      </form>
      {message ? <p className="hint">{message}</p> : null}
    </div>
  );
}
