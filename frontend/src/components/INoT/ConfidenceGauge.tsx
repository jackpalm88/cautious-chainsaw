interface Props {
  confidence: number;
  title?: string;
  subtitle?: string;
  size?: 'sm' | 'md';
}

export default function ConfidenceGauge({ confidence, title, subtitle, size = 'md' }: Props) {
  const percent = Math.round(confidence * 100);
  const radius = size === 'md' ? 80 : 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex items-center justify-center">
        <svg width={radius * 2} height={radius * 2}>
          <circle
            cx={radius}
            cy={radius}
            r={radius - 6}
            stroke="rgba(148, 163, 184, 0.2)"
            strokeWidth={8}
            fill="transparent"
          />
          <circle
            cx={radius}
            cy={radius}
            r={radius - 6}
            stroke={percent > 66 ? '#10b981' : percent > 40 ? '#f59e0b' : '#ef4444'}
            strokeWidth={8}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform={`rotate(-90 ${radius} ${radius})`}
          />
          <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fill="#f8fafc" fontSize={size === 'md' ? 26 : 18}>
            {percent}%
          </text>
        </svg>
      </div>
      {title && <p className="text-sm font-semibold text-white">{title}</p>}
      {subtitle && <p className="max-w-[180px] text-center text-xs text-slate-400">{subtitle}</p>}
    </div>
  );
}
