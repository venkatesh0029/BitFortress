'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { SpendingPolicy, AuditEvent } from '@/lib/types';
import {
  ShieldAlert, ShieldCheck, Lock, AlertTriangle,
  History, Sliders, CheckCircle2, Loader2, RefreshCw, KeyRound, Cpu
} from 'lucide-react';

export default function SecurityPage() {
  const { user, hasRole } = useAuth();
  const [policy, setPolicy] = useState<SpendingPolicy | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [perTxBtc, setPerTxBtc] = useState<string>('0.50');
  const [dailyBtc, setDailyBtc] = useState<string>('2.00');
  const [requireAdmin, setRequireAdmin] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [updateSuccess, setUpdateSuccess] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [chainVerification, setChainVerification] = useState<any>(null);
  const [isVerifyingChain, setIsVerifyingChain] = useState<boolean>(false);

  const loadSecurityData = async () => {
    try {
      const [p, events, verification] = await Promise.all([
        api.getPolicy().catch(() => null),
        api.getAuditTrail(undefined, 50),
        api.verifyAuditTrail().catch(() => null)
      ]);
      if (p) {
        setPolicy(p);
        setPerTxBtc(p.per_tx_btc.toString());
        setDailyBtc(p.daily_btc.toString());
        setRequireAdmin(p.require_admin_override);
      }
      setAuditEvents(events);
      if (verification) setChainVerification(verification);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadSecurityData();
  }, []);

  const handleVerifyChain = async () => {
    setIsVerifyingChain(true);
    try {
      const res = await api.verifyAuditTrail();
      setChainVerification(res);
    } catch (e: any) {
      alert(e.message || 'Verification failed');
    } finally {
      setIsVerifyingChain(false);
    }
  };

  const handleUpdatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    const perTxSats = Math.round(parseFloat(perTxBtc) * 100_000_000);
    const dailySats = Math.round(parseFloat(dailyBtc) * 100_000_000);

    setIsUpdating(true);
    setUpdateSuccess(null);
    try {
      const updated = await api.updatePolicy(perTxSats, dailySats, requireAdmin);
      setPolicy(updated);
      setUpdateSuccess('Corporate spending limits updated and recorded in audit log.');
      await loadSecurityData();
      setTimeout(() => setUpdateSuccess(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Update failed');
    } finally {
      setIsUpdating(false);
    }
  };

  const isAdmin = hasRole(['ORG_ADMIN']);

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyan-900/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Security Center & Audit Log</h1>
            <span className="neon-badge-purple text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
              Policy & Audit
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Configure spending rate limits, inspect policy decisions, and verify immutable audit records
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyChain}
            disabled={isVerifyingChain}
            className="px-4 py-2 rounded-xl bg-purple-950/60 border border-purple-500/40 text-xs text-purple-300 hover:text-white hover:border-purple-400 flex items-center gap-2 transition hover:shadow-[0_0_15px_rgba(168,85,247,0.3)] font-mono font-bold"
          >
            {isVerifyingChain ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />}
            Verify SHA-256 Hash Chain
          </button>

          <button
            onClick={loadSecurityData}
            className="px-4 py-2 rounded-xl bg-slate-900/90 border border-cyan-900/60 text-xs text-cyan-300 hover:text-white hover:border-cyan-400 flex items-center gap-2 transition hover:shadow-[0_0_15px_rgba(0,240,255,0.2)] font-mono font-bold"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            Refresh
          </button>
        </div>
      </div>

      {chainVerification && (
        <div className={`p-4 rounded-xl border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          chainVerification.is_valid
            ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300 shadow-[0_0_20px_rgba(0,255,157,0.1)]'
            : 'bg-rose-950/30 border-rose-500/40 text-rose-300 shadow-[0_0_20px_rgba(255,30,86,0.1)]'
        }`}>
          <div className="flex items-center gap-2.5">
            {chainVerification.is_valid ? (
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
            )}
            <div>
              <div className="font-bold flex items-center gap-2">
                <span>Cryptographic Audit Trail Integrity:</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase ${
                  chainVerification.is_valid ? 'neon-badge-emerald' : 'neon-badge-rose'
                }`}>
                  {chainVerification.is_valid ? '100% Intact / Verified' : 'Integrity Compromised'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">{chainVerification.message}</p>
            </div>
          </div>
          <div className="font-mono text-[10px] text-right text-slate-400 bg-slate-950/60 p-2 rounded-lg border border-cyan-900/30">
            <div>Records Verified: {chainVerification.total_records}</div>
            <div className="text-cyan-400 truncate max-w-xs">Tip: {chainVerification.latest_hash?.slice(0, 20)}...</div>
          </div>
        </div>
      )}

      {updateSuccess && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-xs text-emerald-300 flex items-center gap-2.5 shadow-[0_0_20px_rgba(0,255,157,0.15)]">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="font-medium">{updateSuccess}</span>
        </div>
      )}

      {/* Top Grid: Spending Policies & Quota Meter */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Policy Configuration Form */}
        <div className="lg:col-span-2 p-6 rounded-2xl neon-card space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-cyan-950">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded-xl bg-cyan-950/60 text-cyan-400 border border-cyan-500/30">
                <Sliders className="w-4 h-4" />
              </span>
              <div>
                <h2 className="text-sm font-extrabold text-white tracking-wide">Treasury Spending Policy Engine</h2>
                <p className="text-xs text-slate-400">Strict per-transaction and 24-hour aggregate velocity caps</p>
              </div>
            </div>
            {!isAdmin ? (
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                Read-Only (Admin Required)
              </span>
            ) : (
              <span className="neon-badge-cyan text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                Admin Config
              </span>
            )}
          </div>

          <form onSubmit={handleUpdatePolicy} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Max Single Transaction Cap (BTC)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    min="0.001"
                    disabled={!isAdmin || isUpdating}
                    value={perTxBtc}
                    onChange={e => setPerTxBtc(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-cyan-900/50 text-white font-mono text-xs focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/30 disabled:opacity-50 transition"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-cyan-400 font-bold font-mono">BTC</span>
                </div>
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Proposals exceeding this cap are blocked automatically by policy engine.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  24-Hour Rolling Outflow Cap (BTC)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    disabled={!isAdmin || isUpdating}
                    value={dailyBtc}
                    onChange={e => setDailyBtc(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-cyan-900/50 text-white font-mono text-xs focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/30 disabled:opacity-50 transition"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-cyan-400 font-bold font-mono">BTC</span>
                </div>
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Velocity protection prevents rapid treasury drainage in a rolling window.
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2.5 pt-1">
              <input
                type="checkbox"
                id="adminOverride"
                disabled={!isAdmin || isUpdating}
                checked={requireAdmin}
                onChange={e => setRequireAdmin(e.target.checked)}
                className="w-4 h-4 rounded border-cyan-800 bg-slate-950 text-cyan-400 focus:ring-0 cursor-pointer accent-cyan-400"
              />
              <label htmlFor="adminOverride" className="text-xs text-slate-300 cursor-pointer select-none">
                Require Organization Admin signature override for high-value proposals
              </label>
            </div>

            {isAdmin && (
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="neon-btn-primary px-5 py-2.5 rounded-xl disabled:opacity-50 text-xs font-bold flex items-center gap-2 transition"
                >
                  {isUpdating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                  Save Policy Configuration
                </button>
              </div>
            )}
          </form>
        </div>

        {/* Security Overview Sidebar */}
        <div className="p-6 rounded-2xl neon-card-purple space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-purple-300 flex items-center gap-2">
              <Lock className="w-3.5 h-3.5 text-purple-400" />
              Active Security Guardrails
            </h3>

            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-purple-900/40 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Key Custody:</span>
                <span className="neon-glow-text-emerald font-semibold font-mono text-[11px]">Zero Server Storage</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Signer Quorum:</span>
                <span className="neon-glow-text-cyan font-semibold font-mono text-[11px]">BIP-174 PSBT Standard</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Replay Guard:</span>
                <span className="text-white font-medium font-mono text-[11px]">BIP-143 SegWit Sighash</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Audit Trail:</span>
                <span className="text-purple-300 font-medium font-mono text-[11px]">PostgreSQL Append-Only</span>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-800/40 text-[11px] text-purple-300 flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
            <span>Audit trail records are protected from ordinary user deletion, tamper, or rollback.</span>
          </div>
        </div>
      </div>

      {/* Immutable Audit Trail Log */}
      <div className="p-6 rounded-2xl neon-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-extrabold text-white tracking-wide">System Audit Trail Log</h2>
              <span className="neon-badge-cyan text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
                Append-Only
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Chronological ledger of proposal, signature, policy, and broadcast actions</p>
          </div>
          <span className="text-xs font-mono text-cyan-400 font-bold">{auditEvents.length} events logged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-cyan-950 text-slate-400 uppercase tracking-wider text-[10px] font-mono">
                <th className="pb-3 font-semibold text-cyan-400">ID</th>
                <th className="pb-3 font-semibold">Timestamp</th>
                <th className="pb-3 font-semibold">Action / Event Type</th>
                <th className="pb-3 font-semibold">Acting Custodian</th>
                <th className="pb-3 font-semibold">Reference</th>
                <th className="pb-3 font-semibold">IP Address</th>
                <th className="pb-3 font-semibold text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyan-950/40 font-mono text-[11px]">
              {auditEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-sans text-xs">
                    No audit records logged yet.
                  </td>
                </tr>
              ) : (
                auditEvents.map(evt => (
                  <tr
                    key={evt.id}
                    onClick={() => setSelectedEvent(evt)}
                    className="hover:bg-cyan-950/20 transition cursor-pointer group"
                  >
                    <td className="py-3 text-cyan-400 font-bold group-hover:neon-glow-text-cyan">#{evt.id}</td>
                    <td className="py-3 text-slate-400 whitespace-nowrap font-sans text-[11px]">
                      {new Date(evt.created_at).toLocaleDateString()} {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 font-sans">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        evt.event_type.includes('BROADCAST') || evt.event_type.includes('SUCCESS')
                          ? 'neon-badge-emerald'
                          : evt.event_type.includes('BLOCKED') || evt.event_type.includes('REJECTED')
                          ? 'neon-badge-rose'
                          : evt.event_type.includes('SIGNATURE')
                          ? 'neon-badge-cyan'
                          : 'neon-badge-purple'
                      }`}>
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="py-3 font-sans text-white font-medium">{evt.actor_name || 'System'}</td>
                    <td className="py-3 text-slate-400 font-sans">{evt.reference_type} #{evt.reference_id || '---'}</td>
                    <td className="py-3 text-slate-500 font-mono text-[10px]">{evt.ip_address || '127.0.0.1'}</td>
                    <td className="py-3 text-right text-cyan-400 font-sans font-semibold group-hover:neon-glow-text-cyan">
                      View Payload →
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl neon-card shadow-2xl p-6 space-y-4 border border-cyan-500/30">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-900/40">
              <span className="text-base font-extrabold text-white tracking-wide">
                Audit Event #{selectedEvent.id}
              </span>
              <button
                onClick={() => setSelectedEvent(null)}
                className="w-7 h-7 rounded-lg bg-slate-900 border border-cyan-900/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400 flex items-center justify-center text-xs transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Event Type:</span>
                <span className="neon-badge-cyan px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase">
                  {selectedEvent.event_type}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Acting User:</span>
                <span className="text-white font-medium">{selectedEvent.actor_name || 'System'}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-300 font-mono">{new Date(selectedEvent.created_at).toLocaleString()}</span>
              </div>
              <div className="space-y-1.5 pt-2">
                <span className="text-slate-400">JSON Audit Payload:</span>
                <pre className="p-3.5 rounded-xl bg-slate-950/90 border border-cyan-900/50 text-[11px] font-mono text-cyan-300 overflow-x-auto max-h-56 shadow-[inset_0_2px_8px_rgba(0,0,0,0.6)]">
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </div>
            </div>

            <div className="pt-3 border-t border-cyan-900/40 flex justify-end">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-5 py-2 rounded-xl bg-slate-900 border border-cyan-900/60 hover:border-cyan-400 text-white text-xs font-bold transition hover:neon-glow-text-cyan"
              >
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
