"use client";

import { useState } from "react";
import { Maximize2, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";

const timeRanges = ["1H", "6H", "1D", "1W", "1M", "ALL"];

// Sample data points for the chart
const chartData = [
  { x: 0, y: 55 },
  { x: 5, y: 54 },
  { x: 10, y: 52 },
  { x: 15, y: 52 },
  { x: 20, y: 51 },
  { x: 25, y: 50 },
  { x: 30, y: 50 },
  { x: 35, y: 49 },
  { x: 40, y: 48 },
  { x: 45, y: 47 },
  { x: 50, y: 45 },
  { x: 55, y: 44 },
  { x: 60, y: 43 },
  { x: 65, y: 42 },
  { x: 70, y: 35 },
  { x: 75, y: 30 },
  { x: 80, y: 28 },
  { x: 85, y: 27 },
  { x: 90, y: 26 },
  { x: 95, y: 26 },
  { x: 100, y: 26 },
];

export function PriceChart() {
  const [selectedRange, setSelectedRange] = useState("1D");

  // Convert data to SVG path
  const width = 800;
  const height = 300;
  const padding = { top: 20, right: 60, bottom: 40, left: 20 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const minY = 20;
  const maxY = 60;

  const getX = (x: number) => padding.left + (x / 100) * chartWidth;
  const getY = (y: number) => padding.top + chartHeight - ((y - minY) / (maxY - minY)) * chartHeight;

  const pathD = chartData
    .map((point, i) => `${i === 0 ? "M" : "L"} ${getX(point.x)} ${getY(point.y)}`)
    .join(" ");

  // Gradient area path
  const areaD = `${pathD} L ${getX(100)} ${height - padding.bottom} L ${getX(0)} ${height - padding.bottom} Z`;

  const yLabels = [55, 45, 35, 25];
  const xLabels = ["12:00am", "12:00pm", "12:00am"];

  return (
    <div className="mt-6">
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-primary text-xs font-medium">UP</span>
        <span className="text-primary text-4xl font-bold">26% chance</span>
        <span className="text-destructive text-sm">▼ 27%</span>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.65 0.2 180 / 0.3)" />
              <stop offset="100%" stopColor="oklch(0.65 0.2 180 / 0)" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {yLabels.map((label) => (
            <g key={label}>
              <line
                x1={padding.left}
                y1={getY(label)}
                x2={width - padding.right}
                y2={getY(label)}
                stroke="oklch(0.30 0.025 250)"
                strokeDasharray="4 4"
              />
              <text
                x={width - padding.right + 10}
                y={getY(label) + 4}
                fill="oklch(0.65 0.01 250)"
                fontSize="12"
              >
                {label}%
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {xLabels.map((label, i) => (
            <text
              key={label + i}
              x={padding.left + (i * chartWidth) / 2}
              y={height - 10}
              fill="oklch(0.65 0.01 250)"
              fontSize="12"
              textAnchor="middle"
            >
              {label}
            </text>
          ))}

          {/* Chart area */}
          <path d={areaD} fill="url(#chartGradient)" />

          {/* Chart line */}
          <path
            d={pathD}
            fill="none"
            stroke="oklch(0.65 0.2 180)"
            strokeWidth="2"
          />

          {/* Current point */}
          <circle
            cx={getX(100)}
            cy={getY(26)}
            r="6"
            fill="oklch(0.65 0.2 180)"
            stroke="oklch(0.18 0.02 250)"
            strokeWidth="2"
          />
        </svg>

        {/* Polymarket watermark */}
        <div className="absolute top-4 right-16 flex items-center gap-2 text-muted-foreground">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 18.5L4 16V8.5l8 4v8zm0-9.5L4 7l8-4 8 4-8 4zm8 5.5l-8 4.5v-8l8-4v7.5z" />
          </svg>
          <span className="text-sm font-medium">Polymarket</span>
        </div>
      </div>

      {/* Chart footer */}
      <div className="flex items-center justify-between mt-4">
        <div className="flex items-center gap-3 text-sm">
          <span className="text-primary font-medium">+ NEW</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-foreground font-medium">$41,324 Vol.</span>
          <span className="text-muted-foreground">|</span>
          <span className="text-muted-foreground flex items-center gap-1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            Feb 2, 2026
          </span>
        </div>

        <div className="flex items-center gap-1">
          {timeRanges.map((range) => (
            <Button
              key={range}
              variant="ghost"
              size="sm"
              onClick={() => setSelectedRange(range)}
              className={`px-2 py-1 h-auto text-xs ${
                selectedRange === range
                  ? "text-foreground bg-secondary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {range}
            </Button>
          ))}
          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
            <Maximize2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
