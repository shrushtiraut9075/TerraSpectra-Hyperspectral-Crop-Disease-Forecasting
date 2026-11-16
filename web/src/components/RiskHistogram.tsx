import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { RiskHistogramData } from '../types';
import { BarChart3 } from 'lucide-react';

interface RiskHistogramProps {
  histogram?: RiskHistogramData;
}

export const RiskHistogram: React.FC<RiskHistogramProps> = ({ histogram }) => {
  if (!histogram || !histogram.counts || histogram.counts.length === 0) {
    return null;
  }

  const chartData = histogram.counts.map((count, i) => {
    const minVal = histogram.bins[i];
    const maxVal = histogram.bins[i + 1] ?? minVal + 0.1;
    // Calculate color based on risk severity
    const mid = (minVal + maxVal) / 2;
    let color = '#10b981';
    if (mid > 0.7) color = '#ef4444';
    else if (mid > 0.4) color = '#f59e0b';
    else if (mid > 0.2) color = '#84cc16';

    return {
      bin: `${Math.round(minVal * 100)}-${Math.round(maxVal * 100)}%`,
      count,
      color,
    };
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-medium text-slate-300">
        <span className="flex items-center gap-1.5">
          <BarChart3 className="w-3.5 h-3.5 text-emerald-400" />
          Risk Score Distribution
        </span>
        <span className="text-[10px] text-slate-500 font-mono">Pixel frequency</span>
      </div>

      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -25, bottom: 0 }}>
            <XAxis dataKey="bin" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} interval={1} />
            <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="glass-panel p-2 rounded-lg text-xs shadow-xl border border-white/10">
                      <p className="font-semibold text-white">Range: {data.bin}</p>
                      <p className="text-emerald-400 font-mono font-bold">{data.count.toLocaleString()} pixels</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`bar-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

