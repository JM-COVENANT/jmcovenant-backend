"use client";

import { useMemo, useState } from "react";

import LeadsTable from "../../components/LeadsTable";
import StatCard from "../../components/StatCard";
import UsersTable from "../../components/UsersTable";

function joinUrl(base, path) {
  const cleanBase = (base || "").replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return cleanBase ? `${cleanBase}${cleanPath}` : cleanPath;
}

export default function AdminPage() {
  const [apiKey, setApiKey] = useState("");
  const [status, setStatus] = useState("Voer API-key in en klik op Vernieuwen.");
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [leads, setLeads] = useState([]);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.jmcovenant.nl",
    []
  );

  async function adminFetch(path) {
    const res = await fetch(joinUrl(apiBase, path), {
      headers: { "X-Api-Key": apiKey },
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.success === false) {
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  async function refreshAll() {
    if (!apiKey.trim()) {
      setStatus("Vul eerst je INTERNAL_API_KEY in.");
      return;
    }

    setLoading(true);
    setStatus("Data ophalen...");
    try {
      const statsRes = await adminFetch("/admin/stats");
      const usersRes = await adminFetch("/admin/users");
      const leadsRes = await adminFetch("/admin/leads");

      setStats(statsRes);
      setUsers(usersRes.users || []);
      setLeads(leadsRes.leads || []);
      setStatus("Dashboard bijgewerkt.");
    } catch (err) {
      setStatus(`Fout: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        maxWidth: 1100,
        margin: "20px auto",
        padding: 16,
        fontFamily: "sans-serif",
      }}
    >
      <h1 style={{ marginBottom: 16 }}>JMS Admin Dashboard</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input
          type="password"
          placeholder="INTERNAL_API_KEY"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          style={{ minWidth: 280, padding: 10, borderRadius: 8, border: "1px solid #ccc" }}
        />
        <button
          onClick={refreshAll}
          disabled={loading}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            border: 0,
            background: "#111",
            color: "#fff",
            cursor: "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Bezig..." : "Vernieuwen"}
        </button>
      </div>
      <div style={{ color: "#666", marginBottom: 16 }}>{status}</div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 10,
          marginBottom: 18,
        }}
      >
        <StatCard label="Totaal users" value={stats?.total_users ?? "-"} />
        <StatCard label="Betaalde users" value={stats?.paid_users ?? "-"} />
        <StatCard label="Free users" value={stats?.free_users ?? "-"} />
        <StatCard label="Totale usage" value={stats?.total_usage ?? "-"} />
        <StatCard label="Gemiddelde usage" value={stats?.avg_usage ?? "-"} />
      </div>

      <h3>Top gebruikers</h3>
      <UsersTable users={users} />

      <h3 style={{ marginTop: 18 }}>Recente leads</h3>
      <LeadsTable leads={leads} />
    </main>
  );
}
