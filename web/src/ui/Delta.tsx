export function Delta({ value, suffix }: { value: number | null; suffix?: string }) {
  const cls = value === null ? "flat" : value > 0 ? "up" : value < 0 ? "down" : "flat";
  let text: string;
  if (value === null) text = "—";
  else if (value > 0) text = `▲ +${value}`;
  else if (value < 0) text = `▼ -${Math.abs(value)}`;
  else text = "— 0";
  if (suffix) text += ` ${suffix}`;
  return <span className={`delta ${cls}`}>{text}</span>;
}
