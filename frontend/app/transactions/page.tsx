'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AppLayout from '@/components/AppLayout';
import { api } from '@/lib/api';
import { TransactionProposal } from '@/lib/types';
import {
  Search, Filter, Copy, Check, Send, Sparkles, Activity
} from 'lucide-react';

export default function TransactionsPage() {
  const [proposals, setProposals] = useState<TransactionProposal[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [selectedTx, setSelectedTx] = useState<TransactionProposal | null>(null);
  const [copiedTxid, setCopiedTxid] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadTransactions = async () => {
    try {
      const list = await api.getTransactions();
      setProposals(list);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedTxid(id);
    setTimeout(() => setCopiedTxid(null), 2000);
  };

  const filteredProposals = proposals.filter(p => {
    const matchesSearch =
      p.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.destination.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.txid && p.txid.toLowerCase().includes(searchTerm.toLowerCase())) ||
      p.proposer_name.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'ALL' || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <AppLayout>
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyan-900/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Transaction History & Proposals</h1>
            <span className="neon-badge-cyan text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
              On-Chain Ledger
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Searchable corporate transfer records, cryptographic signing logs, and Regtest broadcast proofs
          </p>
        </div>

        <Link
          href="/transactions/propose"
          className="neon-btn-primary px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition"
        >
          <Send className="w-3.5 h-3.5" />
          Propose Payment
        </Link>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-2xl neon-card flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-cyan-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Search by description, address, or TXID..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-950/80 border border-cyan-900/50 text-white text-xs focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/30 transition placeholder:text-slate-600 font-mono"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-cyan-400" />
          <div className="flex items-center gap-1.5 bg-slate-950/90 p-1 rounded-xl border border-cyan-900/40 text-xs">
            {['ALL', 'PENDING', 'BROADCAST', 'REJECTED'].map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-[11px] font-semibold transition tracking-wider ${
                  statusFilter === st
                    ? 'neon-badge-cyan font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="p-6 rounded-2xl neon-card space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
            <h3 className="text-sm font-bold text-white tracking-wide">Corporate Transfers</h3>
          </div>
          <span className="text-[11px] font-mono text-cyan-400/80 font-bold">
            {filteredProposals.length} Record{filteredProposals.length === 1 ? '' : 's'} Found
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-cyan-950 text-slate-400 uppercase tracking-wider text-[10px] font-mono">
                <th className="pb-3 font-semibold text-cyan-400">ID</th>
                <th className="pb-3 font-semibold">Timestamp</th>
                <th className="pb-3 font-semibold">Description</th>
                <th className="pb-3 font-semibold">Destination Address</th>
                <th className="pb-3 font-semibold">Amount</th>
                <th className="pb-3 font-semibold">Signatures</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">On-Chain TXID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyan-950/40 font-mono">
              {filteredProposals.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans text-xs">
                    No transactions match the selected search or filter criteria.
                  </td>
                </tr>
              ) : (
                filteredProposals.map(p => (
                  <tr
                    key={p.id}
                    onClick={() => setSelectedTx(p)}
                    className="hover:bg-cyan-950/20 transition cursor-pointer group"
                  >
                    <td className="py-3.5 font-bold text-cyan-400 group-hover:neon-glow-text-cyan">#{p.id}</td>
                    <td className="py-3.5 text-slate-400 whitespace-nowrap text-[11px]">
                      {new Date(p.created_at).toLocaleDateString()} {new Date(p.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3.5 font-semibold text-white font-sans max-w-[200px] truncate">{p.description}</td>
                    <td className="py-3.5 text-slate-400 truncate max-w-[150px] text-[11px]">{p.destination}</td>
                    <td className="py-3.5 font-bold text-cyan-300 whitespace-nowrap">
                      {p.amount_btc.toFixed(4)} BTC
                    </td>
                    <td className="py-3.5 text-slate-300 font-bold">
                      <span className={p.approvals_count >= p.threshold ? 'text-emerald-400' : 'text-amber-400'}>
                        {p.approvals_count}
                      </span>
                      /{p.threshold}
                    </td>
                    <td className="py-3.5">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
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
                    <td className="py-3.5 text-right text-[11px] text-cyan-400">
                      {p.txid ? (
                        <div className="flex items-center justify-end gap-1.5" onClick={e => e.stopPropagation()}>
                          <span className="text-cyan-300 font-semibold">{p.txid.slice(0, 14)}...</span>
                          <button
                            onClick={() => handleCopy(p.txid!, p.id.toString())}
                            className="p-1 rounded bg-slate-900 border border-cyan-900/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400 transition"
                            title="Copy TXID"
                          >
                            {copiedTxid === p.id.toString() ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-600 italic">Pending Quorum</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction Details Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl neon-card shadow-2xl p-6 space-y-4 border border-cyan-500/30">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-900/40">
              <div className="flex items-center gap-2">
                <span className="text-base font-extrabold text-white tracking-wide">
                  Proposal #{selectedTx.id} Details
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                  selectedTx.status === 'BROADCAST' ? 'neon-badge-emerald' : 'neon-badge-amber'
                }`}>
                  {selectedTx.status}
                </span>
              </div>
              <button
                onClick={() => setSelectedTx(null)}
                className="w-7 h-7 rounded-lg bg-slate-900 border border-cyan-900/60 text-slate-400 hover:text-cyan-300 hover:border-cyan-400 flex items-center justify-center text-xs transition"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Description:</span>
                <span className="text-white font-medium">{selectedTx.description}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Amount:</span>
                <span className="font-mono text-cyan-300 font-bold">
                  {selectedTx.amount_btc.toFixed(4)} BTC ({selectedTx.amount_satoshis.toLocaleString()} sats)
                </span>
              </div>
              <div className="flex flex-col py-1.5 border-b border-cyan-950/80 gap-1">
                <span className="text-slate-400">Destination Address:</span>
                <span className="font-mono text-cyan-300 break-all select-all text-[11px] p-2 rounded-lg bg-slate-950/80 border border-cyan-900/40">
                  {selectedTx.destination}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Proposer:</span>
                <span className="text-white font-medium">{selectedTx.proposer_name}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
                <span className="text-slate-400">Signature Quorum:</span>
                <span className="text-cyan-400 font-mono font-bold">
                  {selectedTx.approvals_count} of {selectedTx.threshold} signatures collected
                </span>
              </div>
              {selectedTx.txid && (
                <div className="space-y-1.5 py-1.5">
                  <span className="text-slate-400">Regtest Broadcast TXID:</span>
                  <div className="p-3 rounded-xl bg-slate-950/90 border border-cyan-500/30 font-mono text-cyan-300 text-[11px] break-all select-all shadow-[0_0_15px_rgba(0,240,255,0.1)]">
                    {selectedTx.txid}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-cyan-900/40 flex justify-end">
              <button
                onClick={() => setSelectedTx(null)}
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
