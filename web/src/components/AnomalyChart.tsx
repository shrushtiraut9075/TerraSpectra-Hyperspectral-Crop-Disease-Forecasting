import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { AnomalyItem } from '../types';
import { Activity } from 'lucide-react';

interface AnomalyChartProps {
  anomalies?: AnomalyItem[];
}

export const AnomalyChart: React.FC<AnomalyChartProps> = ({ anomalies = [] }) => {
  if (!anomalies || anomalies.length === 0) {
    return null;
  }

  const colors = ['#ef4444', '#f59e0b', '#38bdf8', '#a855f7'];

  const chartData = anomalies.map((item, idx) => ({
    name: item.name,
    sharePercent: Math.round(item.share * 100),
    bands: `${item.bands_nm[0]}-${item.bands_nm[1]} nm`,
    color: colors[idx % colors.length]
  }));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-medium text-slate-300">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-red-400" />
          Physiological Stress Signatures
        </span>
        <span className="text-[10px] text-slate-500 font-mono">Perturbation verified</span>
      </div>

      <div className="h-36 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 10, left: -10, bottom: 0 }}>
            <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 10, fill: '#cbd5e1' }} axisLine={false} tickLine={false} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="glass-panel p-2 rounded-lg text-xs shadow-xl border border-white/10">
                      <p className="font-semibold text-white">{data.name}</p>
                      <p className="text-[11px] text-slate-400 font-mono">Spectral Bands: {data.bands}</p>
                      <p className="text-[11px] text-emerald-400 font-mono font-bold mt-1">Impact Share: {data.sharePercent}%</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="sharePercent" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

