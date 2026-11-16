import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { TimelinePoint } from '../types';

interface TrendSparklineProps {
  points: TimelinePoint[];
  currentSceneId: string | null;
}

export const TrendSparkline: React.FC<TrendSparklineProps> = ({ points, currentSceneId }) => {
  if (!points || points.length === 0) return null;

  const chartData = points.map((p) => {
    const d = new Date(p.acquired_at);
    const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;
    return {
      date: dateStr,
      acres: p.acres_at_risk,
      sceneId: p.scene_id,
      isCurrent: p.scene_id === currentSceneId,
    };
  });

  return (
    <div className="h-14 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 2, left: -25, bottom: 0 }}>
          <defs>
            <linearGradient id="acresRiskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload;
                return (
                  <div className="glass-panel p-1.5 rounded text-[11px] shadow-lg border border-white/10 font-mono">
                    <span className="text-slate-400">{item.date}: </span>
                    <span className="text-red-400 font-bold">{item.acres} acres</span>
                  </div>
                );
              }
              return null;
            }}
          />
          <Area
            type="monotone"
            dataKey="acres"
            stroke="#ef4444"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#acresRiskGradient)"
            dot={(props: any) => {
              const isSelected = props.payload.isCurrent;
              return (
                <circle
                  key={props.key}
                  cx={props.cx}
                  cy={props.cy}
                  r={isSelected ? 4 : 2}
                  fill={isSelected ? '#10b981' : '#ef4444'}
                  stroke={isSelected ? '#ffffff' : '#000000'}
                  strokeWidth={isSelected ? 2 : 1}
                />
              );
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

