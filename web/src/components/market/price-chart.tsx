import {
  Area,
  AreaChart,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export interface ChartPoint {
  time: string;
  index: number;
}

interface PriceChartProps {
  data: ChartPoint[];
  priceUp: number;
  priceDown: number;
  labelUp?: string | null;
  labelDown?: string | null;
  volume?: number;
  windowEnd?: string;
}

export function PriceChart({
  data,
  priceUp,
  priceDown,
  labelUp = "Heating up",
  labelDown = "Cooling down",
  volume,
  windowEnd,
}: PriceChartProps) {
  const upPct = (priceUp * 100).toFixed(0);
  const downPct = (priceDown * 100).toFixed(0);

  return (
    <div className="mt-6">
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-primary text-xs font-medium">{labelUp}</span>
        <span className="text-primary text-4xl font-bold">{upPct}%</span>
        <span className="text-destructive text-sm" title={labelDown ?? undefined}>
          ▼ {downPct}%
        </span>
      </div>

      <div
        className="relative rounded-lg border border-border bg-muted/20 p-4"
        style={{ height: 320 }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <defs>
              <linearGradient
                id="chartGradient"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="0%"
                  stopColor="oklch(0.65 0.2 180 / 0.35)"
                />
                <stop
                  offset="100%"
                  stopColor="oklch(0.65 0.2 180 / 0)"
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="4 4"
              stroke="var(--border)"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              stroke="var(--muted-foreground)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis
              stroke="var(--muted-foreground)"
              fontSize={12}
              domain={["auto", "auto"]}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
              }}
              formatter={(value: number) => [value.toFixed(1), "Index"]}
            />
            <Area
              type="monotone"
              dataKey="index"
              fill="url(#chartGradient)"
              stroke="var(--primary)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 2, stroke: "var(--border)" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">
          {volume != null ? `Vol. ${volume}` : "Attention index"}
        </span>
        {windowEnd && (
          <span>
            {new Date(windowEnd).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </span>
        )}
      </div>
    </div>
  );
}
