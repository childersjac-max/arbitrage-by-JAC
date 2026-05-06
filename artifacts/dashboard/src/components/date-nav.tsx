import { ChevronLeft, ChevronRight } from "lucide-react";
import { useSelectedDate, isSameDay } from "@/lib/date-context";

const NUM_DAYS = 5;

function startOfDay(d: Date): Date {
  const out = new Date(d);
  out.setHours(0, 0, 0, 0);
  return out;
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

function labelFor(d: Date, today: Date): string {
  const diffMs = startOfDay(d).getTime() - startOfDay(today).getTime();
  const diff = Math.round(diffMs / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function DateNav() {
  const { selectedDate, setSelectedDate } = useSelectedDate();
  const today = new Date();

  const days = Array.from({ length: NUM_DAYS }, (_, i) => addDays(today, i));

  const selectedIdx = days.findIndex((d) => isSameDay(d, selectedDate));
  const canGoBack = selectedIdx > 0;
  const canGoForward = selectedIdx < days.length - 1;

  const go = (delta: number) => {
    const next = addDays(selectedDate, delta);
    const clampedIdx = Math.max(0, Math.min(NUM_DAYS - 1, selectedIdx + delta));
    setSelectedDate(days[clampedIdx] ?? next);
  };

  return (
    <div className="border-b border-border bg-card/60 sticky top-14 z-40">
      <div className="container mx-auto px-4 h-9 flex items-center gap-1">
        <button
          onClick={() => go(-1)}
          disabled={!canGoBack}
          className="p-1 rounded hover:bg-secondary disabled:opacity-30 transition-colors"
          aria-label="Previous day"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-0.5 overflow-x-auto no-scrollbar flex-1">
          {days.map((d, i) => {
            const active = isSameDay(d, selectedDate);
            return (
              <button
                key={i}
                onClick={() => setSelectedDate(d)}
                className={`px-3 py-1 rounded text-xs whitespace-nowrap transition-colors font-medium ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
                }`}
              >
                {labelFor(d, today)}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => go(1)}
          disabled={!canGoForward}
          className="p-1 rounded hover:bg-secondary disabled:opacity-30 transition-colors"
          aria-label="Next day"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
