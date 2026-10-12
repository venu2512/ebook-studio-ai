import Link from "next/link";

import { cn } from "@/lib/utils";

export function Logo({
  className,
  showText = true,
  href = "/",
}: {
  className?: string;
  showText?: boolean;
  href?: string;
}) {
  const content = (
    <span className={cn("flex items-center gap-2 font-semibold tracking-tight", className)}>
      <span className="relative grid size-8 place-items-center rounded-lg bg-gradient-to-br from-primary to-fuchsia-500 text-primary-foreground shadow-sm">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden>
          <path
            d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19a1 1 0 0 1 1 1v15a1 1 0 0 1-1 1H6.5A2.5 2.5 0 0 0 4 22.5V5.5Z"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path d="M8 7.5h8M8 11h8M8 14.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </span>
      {showText && <span className="text-[15px]">eBook Studio AI</span>}
    </span>
  );

  if (!href) return content;
  return (
    <Link href={href} className="inline-flex items-center">
      {content}
    </Link>
  );
}
