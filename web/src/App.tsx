import { useEffect, useState } from "react";
import * as api from "./api";
import { LoginPage } from "./pages/Login";
import { Workbench } from "./pages/Workbench";

export function App() {
  const [account, setAccount] = useState<api.Account | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .me()
      .then(setAccount)
      .catch(() => setAccount(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return <div className="boot">加载中</div>;
  }
  if (!account) {
    return <LoginPage onLogin={setAccount} />;
  }
  return <Workbench account={account} onLogout={() => setAccount(null)} />;
}
