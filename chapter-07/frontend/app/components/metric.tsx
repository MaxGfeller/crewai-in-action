export function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function EmptyPanel({ text }: { text: string }) {
  return <p className="empty">{text}</p>;
}
