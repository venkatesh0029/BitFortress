'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { TreasuryWallet, TransactionProposal, AuditEvent, SpendingPolicy } from '@/lib/types';
import {
  Vault, Send, CheckSquare, ArrowUpRight, TrendingUp,
  ShieldCheck, AlertCircle, RefreshCw, KeyRound, Clock,
  ExternalLink, CheckCircle2, XCircle, Zap, Cpu
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';

export default function DashboardPage() {
  const { user } = useAuth();
  const [wallets, setWallets] = useState<TreasuryWallet[]>([]);
  const [proposals, setProposals] = useState<TransactionProposal[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [policy, setPolicy] = useState<SpendingPolicy | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const loadData = async () => {
    try {
      const [tWallets, tProposals, tAudit, tPolicy] = await Promise.all([
        api.getTreasuries(),
        api.getTransactions(),
        api.getAuditTrail(undefined, 8),
        api.getPolicy().catch(() => null)
      ]);
      setWallets(tWallets);
      setProposals(tProposals);
      setAuditEvents(tAudit);
      setPolicy(tPolicy);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    if (wallets.length === 0) return;
    setIsSyncing(true);
    try {
      await api.syncTreasury(wallets[0].id);
      await loadData();
    } finally {
      setIsSyncing(false);
    }
  };

  const primaryWallet = wallets[0] || null;
  const pendingCount = proposals.filter(p => p.status === 'PENDING').length;

  const currentBtc = primaryWallet ? primaryWallet.balance_btc : 0.0;
  const broadcastVolumeToday = proposals
    .filter(p => p.status === 'BROADCAST')
    .reduce((acc, p) => acc + p.amount_btc, 0);

  const days = ['6d ago', '5d ago', '4d ago', '3d ago', '2d ago', 'Yesterday', 'Today'];
  const chartData = days.map((label, idx) => {
    const isToday = idx === 6;
    return {
      day: label,
      balance: currentBtc,
      volume: isToday ? broadcastVolumeToday : 0.0,
    };
  });

  return (
    <AppLayout>
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#00F0FF]/15">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Treasury Operations Overview</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono neon-badge-cyan">
              LIVE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time multisig reserves, signing quorum trajectory, and autonomous spending guardrails
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSync}
            disabled={isSyncing}
            className="px-3.5 py-1.5 rounded-xl bg-[#070D1E] border border-slate-800 hover:border-[#00F0FF]/40 text-xs text-slate-300 hover:text-white flex items-center gap-2 transition hover:shadow-[0_0_15px_rgba(0,240,255,0.2)]"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#00F0FF] ${isSyncing ? 'animate-spin' : ''}`} />
            Sync Node Balance
          </button>

          <Link
            href="/transactions/propose"
            className="px-4 py-2 rounded-xl neon-btn-primary text-xs font-black flex items-center gap-2 transition"
          >
            <Send className="w-3.5 h-3.5" />
            Propose Transfer
          </Link>
        </div>
      </div>

      {/* Primary Neon KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Reserves */}
        <div className="p-5 rounded-2xl neon-card space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#00F0FF]" />
              Treasury Reserve
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#00F0FF]/10 text-[#00F0FF] flex items-center justify-center border border-[#00F0FF]/30 shadow-[0_0_10px_rgba(0,240,255,0.3)]">
              <Vault className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black font-mono text-[#00F0FF] tracking-tight drop-shadow-[0_0_12px_rgba(0,240,255,0.5)]">
              {primaryWallet ? `${primaryWallet.balance_btc.toFixed(4)} BTC` : '10.0000 BTC'}
            </div>
            <div className="text-[11px] font-mono text-slate-400 mt-1 flex items-center justify-between">
              <span>{primaryWallet ? `${primaryWallet.balance_satoshis.toLocaleString()} sats` : '1,000,000,000 sats'}</span>
              <span className="text-[#00FF9D] font-bold drop-shadow-[0_0_8px_rgba(0,255,157,0.5)]">On-chain Regtest</span>
            </div>
          </div>
        </div>

        {/* Quorum Policy */}
        <div className="p-5 rounded-2xl neon-card-purple space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#C084FC]" />
              Quorum Policy
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#A855F7]/10 text-[#C084FC] flex items-center justify-center border border-[#A855F7]/30 shadow-[0_0_10px_rgba(168,85,247,0.3)]">
              <KeyRound className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight drop-shadow-[0_0_10px_rgba(192,132,252,0.4)]">
              {primaryWallet ? `${primaryWallet.threshold}-of-${primaryWallet.total_signers} Quorum` : '2-of-3 Quorum'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between font-mono">
              <span>Native SegWit P2WSH</span>
              <span className="text-[#C084FC] font-bold">ACHIEVABLE</span>
            </div>
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="p-5 rounded-2xl neon-card space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#FFB800]" />
              Pending Quorum
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#FFB800]/10 text-[#FFB800] flex items-center justify-center border border-[#FFB800]/30 shadow-[0_0_10px_rgba(255,184,0,0.3)]">
              <CheckSquare className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
              <span className="text-[#FFB800] font-mono drop-shadow-[0_0_12px_rgba(255,184,0,0.5)]">
                {pendingCount}
              </span>
              {pendingCount > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase neon-badge-amber animate-pulse">
                  Action Required
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              <Link href="/approvals" className="text-[#00F0FF] hover:underline flex items-center gap-1 font-semibold">
                Inspect pending PSBTs →
              </Link>
            </div>
          </div>
        </div>

        {/* Spending Limits */}
        <div className="p-5 rounded-2xl neon-card-emerald space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#00FF9D]" />
              Per-Tx Limit
            </span>
            <div className="w-8 h-8 rounded-lg bg-[#00FF9D]/10 text-[#00FF9D] flex items-center justify-center border border-[#00FF9D]/30 shadow-[0_0_10px_rgba(0,255,157,0.3)]">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black font-mono text-[#00FF9D] tracking-tight drop-shadow-[0_0_12px_rgba(0,255,157,0.5)]">
              {policy ? `${policy.per_tx_btc.toFixed(2)} BTC` : '0.50 BTC'}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center justify-between font-mono">
              <span>Daily: {policy ? `${policy.daily_btc.toFixed(2)} BTC` : '2.00 BTC'}</span>
              <span className="text-slate-400 font-bold">Policy Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Neon Chart & Audit Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Column */}
        <div className="lg:col-span-2 p-6 rounded-2xl neon-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]"></span>
                Treasury Reserve & Velocity Trajectory
              </h2>
              <p className="text-xs text-slate-400">Real-time liquidity telemetry on Bitcoin Core Regtest</p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded-full neon-badge-cyan text-[10px] font-mono font-bold">
                7-DAY METRIC
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="neonCyanGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00F0FF" stopOpacity={0.45} />
                    <stop offset="95%" stopColor="#00F0FF" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#0C1B2E" />
                <XAxis dataKey="day" stroke="#475569" fontSize={11} tickLine={false} />
                <YAxis stroke="#475569" fontSize={11} tickLine={false} domain={[0, 15]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#070D1E', borderColor: 'rgba(0,240,255,0.3)', borderRadius: '0.75rem', fontSize: '12px', boxShadow: '0 0 20px rgba(0,240,255,0.2)' }}
                  itemStyle={{ color: '#00F0FF', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="balance" stroke="#00F0FF" strokeWidth={2.5} fillOpacity={1} fill="url(#neonCyanGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Security Audit Feed */}
        <div className="p-6 rounded-2xl neon-card space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#A855F7] shadow-[0_0_8px_#A855F7]"></span>
                Live Audit Stream
              </h2>
              <Link href="/security" className="text-xs text-[#00F0FF] hover:underline font-semibold">
                Explore →
              </Link>
            </div>

            <div className="space-y-2.5">
              {auditEvents.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-500">No events recorded</div>
              ) : (
                auditEvents.slice(0, 5).map(event => (
                  <div key={event.id} className="p-3 rounded-xl bg-[#030712]/70 border border-slate-800/80 hover:border-[#00F0FF]/30 text-xs space-y-1 transition">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">{event.event_type}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Custodian: <span className="text-[#00F0FF] font-semibold">{event.actor_name || 'System'}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono flex items-center justify-between">
            <span>APPEND-ONLY LEDGER</span>
            <span className="text-[#00FF9D]">IMMUTABLE</span>
          </div>
        </div>
      </div>

      {/* Recent Proposals Table with Neon Highlighting */}
      <div className="p-6 rounded-2xl neon-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FFB800] shadow-[0_0_8px_#FFB800]"></span>
              Active Quorum Pipeline
            </h2>
            <p className="text-xs text-slate-400">Multi-signature withdrawal proposals and cryptographic status</p>
          </div>
          <Link href="/transactions" className="text-xs text-[#00F0FF] hover:underline font-semibold">
            All Transactions →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800/80 text-slate-400 uppercase tracking-wider text-[10px] font-mono">
                <th className="pb-3 font-semibold">Proposal ID</th>
                <th className="pb-3 font-semibold">Description</th>
                <th className="pb-3 font-semibold">Destination Address</th>
                <th className="pb-3 font-semibold">Amount</th>
                <th className="pb-3 font-semibold">Quorum Progress</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {proposals.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No transactions proposed yet. Click &apos;Propose Transfer&apos; to initiate a payment.
                  </td>
                </tr>
              ) : (
                proposals.slice(0, 5).map(p => (
                  <tr key={p.id} className="hover:bg-[#00F0FF]/5 transition">
                    <td className="py-3.5 font-mono text-[#00F0FF] font-bold">#{p.id}</td>
                    <td className="py-3.5 font-semibold text-white">{p.description}</td>
                    <td className="py-3.5 font-mono text-slate-400 truncate max-w-[180px]">{p.destination}</td>
                    <td className="py-3.5 font-mono font-black text-white text-[13px]">
                      {p.amount_btc.toFixed(4)} <span className="text-slate-500 text-[10px]">BTC</span>
                    </td>
                    <td className="py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-[#00F0FF] to-blue-500 h-2 rounded-full shadow-[0_0_8px_#00F0FF]"
                            style={{ width: `${Math.min(100, (p.approvals_count / p.threshold) * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-[#00F0FF] font-bold">
                          {p.approvals_count}/{p.threshold}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          p.status === 'BROADCAST' || p.status === 'CONFIRMED'
                            ? 'neon-badge-emerald'
                            : p.status === 'PENDING'
                            ? 'neon-badge-amber'
                            : p.status === 'REJECTED'
                            ? 'neon-badge-rose'
                            : 'neon-badge-cyan'
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-3.5 text-right">
                      {p.status === 'PENDING' ? (
                        <Link
                          href={`/approvals?id=${p.id}`}
                          className="px-3 py-1 rounded-xl bg-[#00F0FF]/15 hover:bg-[#00F0FF]/30 text-[#00F0FF] border border-[#00F0FF]/40 text-[11px] font-bold transition shadow-[0_0_10px_rgba(0,240,255,0.2)]"
                        >
                          Review & Sign
                        </Link>
                      ) : (
                        <Link
                          href={`/transactions?id=${p.id}`}
                          className="text-slate-400 hover:text-[#00F0FF] text-[11px] font-semibold transition"
                        >
                          Details →
                        </Link>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}
