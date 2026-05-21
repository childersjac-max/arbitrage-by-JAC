import { Link, useLocation } from "wouter";
import { useHealthCheck, useGetArbitrageOpportunities } from "@workspace/api-client-react";
import { Activity } from "lucide-react";
import { DateNav } from "@/components/date-nav";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { data: health } = useHealthCheck();
  const { data: arbData } = useGetArbitrageOpportunities();

  const isConfigured = arbData?.configured ?? false;

  const navLink = (href: string, label: string, extra?: React.ReactNode) => {
    const active = href === "/" ? location === "/" : location.startsWith(href);
    return (
      <Link
        href={href}
        className={`px-3 py-2 text-sm font-medium rounded-md transition-colors flex items-center gap-2 ${
          active
            ? "bg-secondary text-foreground"
            : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
        }`}
      >
        {label}
        {extra}
      </Link>
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="border-b border-border bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 mr-4">
              <Activity className="h-5 w-5 text-primary" />
              <span className="font-bold tracking-tight text-lg">BPR Model</span>
            </div>

            <nav className="flex space-x-1">
              {navLink("/", "Line Tracker")}
              {navLink("/nba", "NBA Model")}
              {navLink(
                "/arbitrage",
                "Arbitrage",
                isConfigured ? (
                  <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                ) : undefined,
              )}
            </nav>
          </div>

          <div className="flex items-center space-x-4 text-xs font-mono text-muted-foreground">
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  health?.status === "ok" ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span>SYS {health?.status === "ok" ? "OK" : "ERR"}</span>
            </div>
          </div>
        </div>
      </header>

      <DateNav />

      <main className="flex-1 p-4 md:p-6 overflow-x-hidden">{children}</main>
    </div>
  );
}
