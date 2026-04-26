export default function LeadsTable({ leads }) {
  const rows = Array.isArray(leads) ? leads : [];

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
          <th style={th}>Datum</th>
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr>
            <td colSpan={2} style={td}>
              Geen leads gevonden
            </td>
          </tr>
        ) : (
          rows.slice(0, 25).map((lead, idx) => (
            <tr key={`${lead.email || "lead"}-${idx}`}>
              <td style={td}>{lead.email || "-"}</td>
              <td style={td}>{lead.date || "-"}</td>
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
