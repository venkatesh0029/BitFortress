'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { api } from '@/lib/api';
import { TreasuryWallet, TransactionProposal } from '@/lib/types';
import {
  BarChart3, TrendingUp, Clock, ShieldCheck,
  CheckCircle2, XCircle, ArrowUpRight, Award, Zap
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend
} from 'recharts';

export default function AnalyticsPage() {
  const [wallets, setWallets] = useState<TreasuryWallet[]>([]);
  const [proposals, setProposals] = useState<TransactionProposal[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [wList, pList] = await Promise.all([
          api.getTreasuries(),
          api.getTransactions()
        ]);
        setWallets(wList);
        setProposals(pList);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const totalBalance = wallets.reduce((acc, w) => acc + w.balance_btc, 0);
  const totalApproved = proposals.filter(p => p.status === 'BROADCAST' || p.status === 'CONFIRMED').length;
  const totalRejected = proposals.filter(p => p.status === 'REJECTED').length;
  const totalPending = proposals.filter(p => p.status === 'PENDING').length;

  const volumeTrendData = [
    { period: 'Week 1', outflow: 0.15, reserve: 10.0 },
    { period: 'Week 2', outflow: 0.40, reserve: 9.85 },
    { period: 'Week 3', outflow: 0.25, reserve: 9.45 },
    { period: 'Week 4', outflow: 0.60, reserve: 9.20 },
    { period: 'Week 5', outflow: 0.10, reserve: 8.60 },
    { period: 'Current', outflow: 0.35, reserve: totalBalance || 10.0 },
  ];

  const signerParticipationData = [
    { name: 'David Kim (HSM-01)', approvals: 8, rejections: 0 },
    { name: 'Elena Rostova (HSM-02)', approvals: 7, rejections: 1 },
    { name: 'Marcus Vance (HSM-03)', approvals: 6, rejections: 0 },
    { name: 'Sarah Lin (Admin)', approvals: 2, rejections: 0 },
  ];

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyan-900/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Treasury Analytics & Governance</h1>
            <span className="neon-badge-cyan text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
              Live Telemetry
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Operational metrics, signer participation rates, and cryptographic treasury liquidity velocity
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl neon-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Total Reserves</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-extrabold font-mono text-white neon-glow-text-cyan">
            {totalBalance.toFixed(4)} BTC
          </div>
          <div className="text-[11px] text-emerald-400 font-mono font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            100% Multisig Quorum Cold
          </div>
        </div>

        <div className="p-5 rounded-2xl neon-card-purple space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Quorum Latency</span>
            <Clock className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-extrabold text-white font-mono neon-glow-text-purple">4.2 min</div>
          <div className="text-[11px] text-purple-300 font-mono">Time to reach threshold</div>
        </div>

        <div className="p-5 rounded-2xl neon-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Quorum Success</span>
            <Award className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-extrabold text-white font-mono">
            {proposals.length > 0 ? `${Math.round((totalApproved / proposals.length) * 100)}%` : '100%'}
          </div>
          <div className="text-[11px] text-cyan-400 font-mono">Approved & Broadcast</div>
        </div>

        <div className="p-5 rounded-2xl neon-card-emerald space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Policy Integrity</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-400 font-mono neon-glow-text-emerald">100.0%</div>
          <div className="text-[11px] text-emerald-300 font-mono">0 unauthorized disbursements</div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Outflow vs Reserve Trend */}
        <div className="p-6 rounded-2xl neon-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wide">Treasury Reserve & Outflow Velocity</h2>
              <p className="text-xs text-slate-400">Weekly capital movement trajectory (BTC)</p>
            </div>
            <span className="neon-badge-cyan text-[10px] font-mono px-2 py-0.5 rounded font-bold">
              REGTEST-BTC
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeTrendData}>
                <defs>
                  <linearGradient id="neonCyanGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00F0FF" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#00F0FF" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0, 240, 255, 0.1)" />
                <XAxis dataKey="period" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#070D1E',
                    borderColor: 'rgba(0, 240, 255, 0.4)',
                    boxShadow: '0 0 20px rgba(0, 240, 255, 0.2)',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                    fontFamily: 'monospace'
                  }}
                  itemStyle={{ color: '#00F0FF' }}
                />
                <Area
                  type="monotone"
                  dataKey="outflow"
                  stroke="#00F0FF"
                  strokeWidth={2.5}
                  fill="url(#neonCyanGrad)"
                  name="Outflow (BTC)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Signer Participation Chart */}
        <div className="p-6 rounded-2xl neon-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wide">Signer Participation & Activity</h2>
              <p className="text-xs text-slate-400">Audit of signatures and vetoes cast per authorized HSM signer</p>
            </div>
            <span className="neon-badge-purple text-[10px] font-mono px-2 py-0.5 rounded font-bold">
              HSM METRICS
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={signerParticipationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(168, 85, 247, 0.12)" />
                <XAxis dataKey="name" stroke="#64748B" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#070D1E',
                    borderColor: 'rgba(168, 85, 247, 0.4)',
                    boxShadow: '0 0 20px rgba(168, 85, 247, 0.2)',
                    borderRadius: '0.75rem',
                    fontSize: '12px',
                    fontFamily: 'monospace'
                  }}
                  itemStyle={{ color: '#F8FAFC' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar dataKey="approvals" fill="#00F0FF" name="Valid PSBT Signatures" radius={[4, 4, 0, 0]} />
                <Bar dataKey="rejections" fill="#FF1E56" name="Rejections / Vetoes" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
