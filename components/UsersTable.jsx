export default function UsersTable({ users }) {
  const rows = Array.isArray(users) ? users : [];

  return (
    <table
      style={{
        width: "100%",
        borderCollapse: "collapse",
        background: "#fff",
        border: "1px solid #e5e5e5",
        borderRadius: 10,
        overflow: "hidden",
      }}
    >
      <thead>
        <tr style={{ background: "#f6f6f6" }}>
          <th style={th}>Email</th>
          <th style={th}>Paid</th>
          <th style={th}>Usage</th>
          <th style={th}>Updated</th>
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={4} style={td}>
              Geen users gevonden
            </td>
          </tr>
        ) : (
          rows.slice(0, 25).map((u) => (
            <tr key={u.email}>
              <td style={td}>{u.email}</td>
              <td style={td}>{u.is_paid ? "Ja" : "Nee"}</td>
              <td style={td}>{u.usage_count ?? 0}</td>
              <td style={td}>{u.updated_at || "-"}</td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
}

const th = {
  textAlign: "left",
  padding: 10,
  borderBottom: "1px solid #eee",
  fontSize: 14,
};

const td = {
  textAlign: "left",
  padding: 10,
  borderBottom: "1px solid #eee",
  fontSize: 14,
};
