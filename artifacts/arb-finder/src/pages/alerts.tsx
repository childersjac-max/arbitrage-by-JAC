import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useAlerts,
  useCreateAlert,
  useDeleteAlert,
  useOJSports,
} from "@/hooks/use-oddsjam";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatPercent } from "@/lib/format";
import { Trash2, BellRing, Plus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const alertSchema = z.object({
  minProfitPercent: z.coerce.number().min(0.1).max(100),
  sport: z.string().optional().transform(val => val === "all" ? undefined : val),
  market: z.string().optional().transform(val => val === "all" ? undefined : val),
});

type AlertFormValues = z.infer<typeof alertSchema>;

export default function Alerts() {
  const { toast } = useToast();

  const { data: alerts, isLoading: isLoadingAlerts } = useAlerts();
  const { data: sports } = useOJSports();

  const createAlert = useCreateAlert();
  const deleteAlert = useDeleteAlert();
  
  const form = useForm<AlertFormValues>({
    resolver: zodResolver(alertSchema),
    defaultValues: {
      minProfitPercent: 1.0,
      sport: "all",
      market: "all",
    },
  });

  const onSubmit = (data: AlertFormValues) => {
    createAlert.mutate(
      {
        minProfitPercent: data.minProfitPercent,
        sport: data.sport,
        market: data.market,
      },
      {
      onSuccess: () => {
        toast({
          title: "Alert created",
          description: "You will be notified of opportunities matching these criteria.",
        });
        form.reset({
          minProfitPercent: 1.0,
          sport: "all",
          market: "all",
        });
      },
      onError: () => {
        toast({
          title: "Error",
          description: "Failed to create alert.",
          variant: "destructive",
        });
      },
    },
    );
  };

  const handleDelete = (id: string) => {
    deleteAlert.mutate(id, {
      onSuccess: () => {
        toast({
          title: "Alert deleted",
          description: "The alert has been removed.",
        });
      },
    });
  };

  const activeSports = sports?.filter(s => s.active) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Alert Configuration</h1>
        <p className="text-muted-foreground">Set up automated alerts for arbitrage opportunities that meet your criteria.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              New Alert
            </CardTitle>
            <CardDescription>Define criteria for a new arbitrage alert.</CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="minProfitPercent"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Minimum Profit (%)</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.1" {...field} data-testid="input-min-profit" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="sport"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Sport (Optional)</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger data-testid="select-alert-sport">
                            <SelectValue placeholder="All Sports" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="all">All Sports</SelectItem>
                          {activeSports.map(sport => (
                            <SelectItem key={sport.key} value={sport.key}>{sport.title}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="market"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Market (Optional)</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger data-testid="select-alert-market">
                            <SelectValue placeholder="All Markets" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="all">All Markets</SelectItem>
                          <SelectItem value="h2h">Moneyline (H2H)</SelectItem>
                          <SelectItem value="spreads">Spreads</SelectItem>
                          <SelectItem value="totals">Totals</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <Button 
                  type="submit" 
                  className="w-full" 
                  disabled={createAlert.isPending}
                  data-testid="button-create-alert"
                >
                  {createAlert.isPending ? "Creating..." : "Create Alert"}
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BellRing className="h-5 w-5" />
              Active Alerts
            </CardTitle>
            <CardDescription>Manage your configured arbitrage alerts.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingAlerts ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : !alerts || alerts.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground border border-dashed border-border rounded-md bg-secondary/10">
                You have no active alerts configured.
              </div>
            ) : (
              <div className="rounded-md border border-border">
                <Table>
                  <TableHeader className="bg-secondary/50">
                    <TableRow>
                      <TableHead>Target Profit</TableHead>
                      <TableHead>Filters</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="w-[80px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {alerts.map((alert) => (
                      <TableRow key={alert.id} data-testid={`row-alert-${alert.id}`}>
                        <TableCell className="font-bold text-success font-mono text-base">
                          &ge; {formatPercent(alert.minProfitPercent)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {alert.sport ? (
                              <Badge variant="secondary" className="font-mono">{alert.sport}</Badge>
                            ) : (
                              <Badge variant="outline" className="text-muted-foreground">Any Sport</Badge>
                            )}
                            {alert.market ? (
                              <Badge variant="secondary" className="font-mono">{alert.market}</Badge>
                            ) : (
                              <Badge variant="outline" className="text-muted-foreground">Any Market</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {formatDate(alert.createdAt)}
                        </TableCell>
                        <TableCell>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            onClick={() => handleDelete(alert.id)}
                            disabled={deleteAlert.isPending}
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            data-testid={`button-delete-alert-${alert.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
