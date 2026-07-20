import Link from "next/link";
import {
  BrainCircuit,
  BookOpen,
  CircleHelp,
  FileText,
  Gauge,
  History,
  Library,
  ListChecks,
  MessageSquare,
  Network,
  Puzzle,
  TrendingUp,
  UploadCloud
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "分析大屏", icon: Gauge },
  { href: "/papers/upload", label: "上传论文", icon: UploadCloud },
  { href: "/papers", label: "论文库", icon: Library },
  { href: "/chat", label: "论文问答", icon: MessageSquare },
  { href: "/notes", label: "阅读笔记", icon: BookOpen },
  { href: "/related-work", label: "相关工作", icon: Network },
  { href: "/memories", label: "研究记忆", icon: BrainCircuit },
  { href: "/skills", label: "分析技能", icon: Puzzle },
  { href: "/learning", label: "学习审核", icon: ListChecks },
  { href: "/policy", label: "策略学习", icon: TrendingUp },
  { href: "/traces", label: "执行追踪", icon: History },
  { href: "/manual", label: "用户手册", icon: CircleHelp }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#eef2f3] text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-slate-800 bg-[#111827] text-slate-100 lg:block">
        <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-5">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-cyan-400/15 text-cyan-300">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <span className="block text-base font-semibold">PaperHermes</span>
            <span className="text-xs text-slate-400">论文智能分析平台</span>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <Link
              href={item.href}
              key={item.href}
              className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-60">
        <header className="sticky top-0 z-10 flex h-16 items-center border-b border-slate-200 bg-white/90 px-5 backdrop-blur">
          <div className="text-sm font-medium text-slate-700">科研论文智能分析工作台</div>
        </header>
        <main className="mx-auto max-w-[1600px] px-5 py-6">{children}</main>
      </div>
    </div>
  );
}
