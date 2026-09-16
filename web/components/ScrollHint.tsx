"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

/* ScrollHint — wrapper for horizontally scrollable rows (week pills).
   Applies the .scroll-hint-x edge-fade affordance and drops it once the
   row is scrolled to the end or fits without scrolling. */
export function ScrollHint({
  children,
  className,
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) {
  const ref = useRef<HTMLDivElement>(null);
  const [atEnd, setAtEnd] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => {
      setAtEnd(el.scrollWidth - el.scrollLeft - el.clientWidth <= 8);
    };
    update();
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return (
    <div
      ref={ref}
      data-at-end={atEnd}
      className={cn("scroll-hint-x", className)}
      {...rest}
    >
      {children}
    </div>
  );
}
