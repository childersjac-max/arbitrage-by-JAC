import { ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { Activity, Bell, ListTree, TrendingUp, Zap } from "lucide-react";
import { useHealthCheck } from "@workspace/api-client-react";
import { cn } from "@/lib/utils";

interface ShellProps {
  children: ReactNode;
}

export default function Shell({ children }: ShellProps) {
  const [location] = useLocation();
  const { data: health } = useHealthCheck({
    query: {
      queryKey: ["health-check"],
      refetchInterval: 30000,
    }
  });

  const isHealthy = health?.status === "ok";

  const navItems = [
    { href: "/", label: "Arbitrage", icon: TrendingUp },
    { href: "/odds", label: "Live Odds", icon: Activity },
    { href: "/alerts", label: "Alerts", icon: Bell },
    { href: "/sports", label: "Sports", icon: ListTree },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <header className="border-b border-border sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 max-w-screen-2xl items-center">
          <div className="mr-4 flex items-center gap-2">
            <Zap className="h-5 w-5 text-success" />
            <span className="font-bold tracking-tight text-lg">OddsTerminal</span>
          </div>
          <nav className="flex items-center gap-1 text-sm font-medium">
            {navItems.map((item) => (
              <Link 
                key={item.href}
                href={item.href}
                className={cn(
                  "transition-colors hover:text-foreground/80 px-4 py-2 rounded-md",
                  location === item.href ? "bg-secondary text-foreground" : "text-foreground/60"
                )}
                data-testid={`nav-${item.label.toLowerCase().replace(" ", "-")}`}
              >
                <div className="flex items-center gap-2">
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </div>
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground" data-testid="status-api">
              <div className={cn("h-2 w-2 rounded-full", isHealthy ? "bg-success" : "bg-destructive")} />
              {isHealthy ? "API Connected" : "API Disconnected"}
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 w-full max-w-screen-2xl mx-auto p-4 md:p-6">
        {children}
      </main>
    </div>
  );
}
