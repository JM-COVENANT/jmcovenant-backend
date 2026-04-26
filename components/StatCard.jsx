export default function StatCard({ label, value }) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e5e5e5",
        borderRadius: 10,
        padding: 14,
      }}
    >
      <div style={{ color: "#666", fontSize: 13, marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: "bold" }}>{value ?? "-"}</div>
    </div>
  );
}
