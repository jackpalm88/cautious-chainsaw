interface PreviewBannerProps {
  mode: 'live' | 'mock';
}

export default function PreviewBanner({ mode }: PreviewBannerProps) {
  if (mode !== 'mock') {
    return null;
  }

  return (
    <div className="mb-4 rounded-xl border border-amber-500/60 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
      <p className="font-semibold">Preview mode enabled</p>
      <p className="mt-1 text-amber-200/90">
        The dashboard is streaming mock data locally. Start the Flask Socket.IO backend and run
        <code className="mx-1 rounded bg-slate-950 px-1.5 py-0.5 text-xs text-amber-100">npm run dev</code>
        for live trading telemetry.
      </p>
      <p className="mt-2 text-amber-200/70">
        Need a quick look without the backend? Use
        <code className="mx-1 rounded bg-slate-950 px-1.5 py-0.5 text-xs text-amber-100">npm run dev:mock</code>
        or build once and preview with
        <code className="mx-1 rounded bg-slate-950 px-1.5 py-0.5 text-xs text-amber-100">npm run preview:mock</code>.
      </p>
    </div>
  );
}
