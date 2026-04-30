import { useState } from "react";
import { useGetSports, useGetOdds } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/format";
import { Activity } from "lucide-react";

export default function Odds() {
  const [selectedSport, setSelectedSport] = useState<string>("americanfootball_nfl");
  const [selectedMarket, setSelectedMarket] = useState<string>("h2h");

  const { data: sports, isLoading: isLoadingSports } = useGetSports();
  const { data: games, isLoading: isLoadingOdds } = useGetOdds(
    { sport: selectedSport, markets: selectedMarket },
    { query: { queryKey: ["odds", selectedSport, selectedMarket], enabled: !!selectedSport } }
  );

  const activeSports = sports?.filter(s => s.active) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Live Market Odds</h1>
        <p className="text-muted-foreground">Compare live odds across bookmakers for selected sports.</p>
      </div>

      <Card>
        <CardHeader className="bg-secondary/30 pb-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <div className="w-full sm:w-64">
              <label className="text-xs text-muted-foreground mb-1 block">Sport</label>
              <Select value={selectedSport} onValueChange={setSelectedSport} disabled={isLoadingSports}>
                <SelectTrigger data-testid="select-sport">
                  <SelectValue placeholder="Select a sport" />
                </SelectTrigger>
                <SelectContent>
                  {activeSports.map(sport => (
                    <SelectItem key={sport.key} value={sport.key}>
                      {sport.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-full sm:w-64">
              <label className="text-xs text-muted-foreground mb-1 block">Market</label>
              <Select value={selectedMarket} onValueChange={setSelectedMarket}>
                <SelectTrigger data-testid="select-market">
                  <SelectValue placeholder="Select a market" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="h2h">Moneyline (H2H)</SelectItem>
                  <SelectItem value="spreads">Spreads</SelectItem>
                  <SelectItem value="totals">Totals (Over/Under)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoadingOdds ? (
            <div className="p-6 space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="border border-border rounded-md p-4 space-y-4">
                  <Skeleton className="h-6 w-1/3" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ))}
            </div>
          ) : !games || games.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border-t border-border border-dashed m-6 rounded-md bg-secondary/20">
              <Activity className="h-10 w-10 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold">No active games found</h3>
              <p className="text-muted-foreground max-w-sm mt-1">There are no games with available odds for this sport and market combination right now.</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {games.map(game => {
                const bookmakers = Array.from(new Set(game.bookmakerOdds.map(o => o.bookmakerTitle)));
                const outcomes = Array.from(new Set(game.bookmakerOdds.map(o => o.outcome)));

                return (
                  <div key={game.id} className="p-6" data-testid={`game-odds-${game.id}`}>
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-lg font-semibold">{game.homeTeam} vs {game.awayTeam}</h3>
                        <div className="text-sm text-muted-foreground">{formatDate(game.commenceTime)}</div>
                      </div>
                      <Badge>{game.sport}</Badge>
                    </div>

                    <div className="border border-border rounded-md overflow-hidden overflow-x-auto">
                      <Table>
                        <TableHeader className="bg-secondary/50">
                          <TableRow>
                            <TableHead className="w-48">Bookmaker</TableHead>
                            {outcomes.map(outcome => (
                              <TableHead key={outcome} className="text-right">{outcome}</TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {bookmakers.map(bookmaker => (
                            <TableRow key={bookmaker}>
                              <TableCell className="font-medium">{bookmaker}</TableCell>
                              {outcomes.map(outcome => {
                                const odd = game.bookmakerOdds.find(o => o.bookmakerTitle === bookmaker && o.outcome === outcome);
                                return (
                                  <TableCell key={`${bookmaker}-${outcome}`} className="text-right font-mono">
                                    {odd ? (
                                      <div className="flex flex-col items-end">
                                        <span>{odd.price > 0 ? `+${odd.price}` : odd.price}</span>
                                        {odd.point != null && <span className="text-xs text-muted-foreground">({odd.point > 0 ? `+${odd.point}` : odd.point})</span>}
                                      </div>
                                    ) : "-"}
                                  </TableCell>
                                );
                              })}
                            </TableRow>
                          ))}
                          {bookmakers.length === 0 && (
                            <TableRow>
                              <TableCell colSpan={outcomes.length + 1} className="text-center text-muted-foreground py-4">
                                No bookmaker data available for this market
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
