import { useEffect, useState } from "react";

export default function Leaderboard() {
  const [rows, setRows] = useState([]);

  useEffect(() => {
    fetch("/api/leaderboard").then((r) => r.json()).then(setRows);
  }, []);

  return (
    <table>
      <thead>
        <tr><th>Recruiter</th><th>Closed vacancies</th></tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}><td>{r.name}</td><td>{r.closed}</td></tr>
        ))}
      </tbody>
    </table>
  );
}
