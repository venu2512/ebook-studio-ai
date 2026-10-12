"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const TABS = [
  { segment: "", label: "Overview" },
  { segment: "outline", label: "Outline" },
  { segment: "generate", label: "Generate" },
  { segment: "workspace", label: "Workspace" },
  { segment: "cover", label: "Cover" },
  { segment: "export", label: "Export" },
  { segment: "marketing", label: "Marketing" },
];

export function BookNav({ bookId }: { bookId: string }) {
  const pathname = usePathname();
  const base = `/books/${bookId}`;

  return (
    <div className="mb-6 flex gap-1 overflow-x-auto border-b pb-px">
      {TABS.map((tab) => {
        const href = tab.segment ? `${base}/${tab.segment}` : base;
        const active = tab.segment
          ? pathname.startsWith(href)
          : pathname === base;
        return (
          <Link
            key={tab.segment || "overview"}
            href={href}
            className={cn(
              "whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
