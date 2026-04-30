import { useOJSports } from "@/hooks/use-oddsjam";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { Search } from "lucide-react";

export default function Sports() {
  const { data: sports, isLoading } = useOJSports();
  const [search, setSearch] = useState("");

  const filteredSports = sports?.filter(s =>
    s.title.toLowerCase().includes(search.toLowerCase()) ||
    s.group.toLowerCase().includes(search.toLowerCase())
  );

  const sportsByGroup = filteredSports?.reduce((acc, sport) => {
    if (!acc[sport.group]) acc[sport.group] = [];
    acc[sport.group]!.push(sport);
    return acc;
  }, {} as Record<string, typeof sports>) || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight">Supported Sports</h1>
          <p className="text-muted-foreground">Directory of all sports and leagues tracked by Optic Odds.</p>
        </div>
        <div className="relative w-full sm:w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search sports..."
            className="pl-9 bg-card"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="input-search-sports"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-1/2 mb-2" />
                <Skeleton className="h-4 w-1/3" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : Object.keys(sportsByGroup).length === 0 ? (
        <div className="text-center py-20 text-muted-foreground border border-dashed border-border rounded-md bg-secondary/10">
          No sports found matching your search.
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Object.entries(sportsByGroup).sort().map(([group, groupSports]) => (
            <Card key={group} className="flex flex-col">
              <CardHeader className="pb-3 border-b border-border bg-secondary/20">
                <CardTitle>{group}</CardTitle>
                <CardDescription>{groupSports?.length} leagues</CardDescription>
              </CardHeader>
              <CardContent className="p-0 flex-1 flex flex-col">
                <div className="divide-y divide-border overflow-y-auto max-h-[400px]">
                  {groupSports?.map(sport => (
                    <div key={sport.key} className="p-4 flex items-center justify-between hover:bg-secondary/30 transition-colors" data-testid={`sport-item-${sport.key}`}>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-sm">{sport.title}</span>
                        <span className="text-xs text-muted-foreground font-mono truncate max-w-[180px]">{sport.key}</span>
                      </div>
                      <div className="flex gap-2">
                        {sport.active
                          ? <Badge variant="secondary" className="bg-success/20 text-success border-0 hover:bg-success/30">Active</Badge>
                          : <Badge variant="outline" className="text-muted-foreground">Inactive</Badge>
                        }
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
