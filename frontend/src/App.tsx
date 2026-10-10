import { useEffect, useState } from "react";

export default function App() {
  const [backend, setBackend] = useState("checking…");

  useEffect(() => {
    fetch("/healthz")
      .then((res) => setBackend(res.ok ? "ok" : `error ${res.status}`))
      .catch(() => setBackend("unreachable"));
  }, []);

  return (
    <main>
      <h1>Rekindle</h1>
      <p>Spark on K8s 故障分診與自動復原平台</p>
      <p>Backend: {backend}</p>
    </main>
  );
}
