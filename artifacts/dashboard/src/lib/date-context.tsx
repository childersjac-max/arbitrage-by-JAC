import { createContext, useContext, useState, type ReactNode } from "react";

export interface DateContextValue {
  selectedDate: Date;
  setSelectedDate: (d: Date) => void;
}

const DateContext = createContext<DateContextValue | null>(null);

function startOfDay(d: Date): Date {
  const out = new Date(d);
  out.setHours(0, 0, 0, 0);
  return out;
}

export function DateProvider({ children }: { children: ReactNode }) {
  const [selectedDate, setSelectedDate] = useState<Date>(() => startOfDay(new Date()));
  return (
    <DateContext.Provider value={{ selectedDate, setSelectedDate }}>
      {children}
    </DateContext.Provider>
  );
}

export function useSelectedDate(): DateContextValue {
  const ctx = useContext(DateContext);
  if (!ctx) throw new Error("useSelectedDate must be used inside DateProvider");
  return ctx;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function startOfDayLocal(d: Date): Date {
  return startOfDay(d);
}
