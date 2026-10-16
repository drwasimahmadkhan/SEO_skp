export default function ScoreRing({ label, value, size = 96 }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value ?? 0));
  const offset = c - (pct / 100) * c;
  const color =
    pct >= 90 ? '#2f6b4f' : pct >= 75 ? '#1a4a6e' : pct >= 50 ? '#c45c26' : '#8b2e2e';

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="rotate-[-90deg]">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e8eef4" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={c}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-display text-2xl text-ink">{Math.round(pct)}</span>
        </div>
      </div>
      <div className="text-sm font-semibold text-sea">{label}</div>
    </div>
  );
}
