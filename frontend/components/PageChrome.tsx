export function PageHeader({
  title,
  description,
  action,
  icon
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-center md:justify-between">
      <div className="flex min-w-0 items-start gap-4">
        {icon ? <div className="grid h-11 w-11 shrink-0 place-items-center rounded-md bg-moss/10 text-moss [&_svg]:h-5 [&_svg]:w-5">{icon}</div> : null}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-normal text-ink md:text-3xl">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function StatCard({
  label,
  value,
  icon,
  tone = "moss"
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  tone?: "moss" | "rust" | "blue" | "slate";
}) {
  const toneClass = {
    moss: "bg-moss/10 text-moss",
    rust: "bg-rust/10 text-rust",
    blue: "bg-bluegray/10 text-bluegray",
    slate: "bg-slate-100 text-slate-600"
  }[tone];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className={`mb-3 grid h-9 w-9 place-items-center rounded-md ${toneClass} [&_svg]:h-4 [&_svg]:w-4`}>{icon}</div>
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1 truncate text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}

export function StatusPill({ label, tone = "slate" }: { label: string; tone?: "green" | "amber" | "red" | "slate" }) {
  const toneClass = {
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    red: "border-red-200 bg-red-50 text-red-700",
    slate: "border-slate-200 bg-slate-50 text-slate-600"
  }[tone];

  return <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold ${toneClass}`}>{label}</span>;
}

export function EmptyState({
  title,
  description,
  icon,
  action
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <div className="mb-4 grid h-12 w-12 place-items-center rounded-md bg-white text-slate-500 shadow-sm [&_svg]:h-6 [&_svg]:w-6">{icon}</div>
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
