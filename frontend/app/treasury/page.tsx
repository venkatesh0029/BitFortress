'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { api } from '@/lib/api';
import { TreasuryWallet } from '@/lib/types';
import {
  Vault, Plus, Copy, Check, RefreshCw, KeyRound,
  Download, ArrowDownToLine, Loader2, ShieldCheck, AlertCircle, Zap
} from 'lucide-react';

export default function TreasuryPage() {
  const [wallets, setWallets] = useState<TreasuryWallet[]>([]);
  const [signersList, setSignersList] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);
  const [isFunding, setIsFunding] = useState<boolean>(false);
  const [fundSuccess, setFundSuccess] = useState<string | null>(null);

  // Create Wallet Modal State
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [walletName, setWalletName] = useState('');
  const [threshold, setThreshold] = useState<number>(2);
  const [selectedSignerIds, setSelectedSignerIds] = useState<number[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState<boolean>(false);

  const loadData = async () => {
    try {
      const [wList, sList] = await Promise.all([
        api.getTreasuries(),
        api.getSigners()
      ]);
      setWallets(wList);
      setSignersList(sList);
      if (sList.length > 0 && selectedSignerIds.length === 0) {
        setSelectedSignerIds(sList.slice(0, 3).map(s => s.id));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const currentWallet = wallets[0] || null;

  const handleCopyAddress = () => {
    if (!currentWallet) return;
    navigator.clipboard.writeText(currentWallet.address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFund = async () => {
    if (!currentWallet) return;
    setIsFunding(true);
    setFundSuccess(null);
    try {
      const res = await api.fundTreasury(currentWallet.id, 5.0);
      setFundSuccess(`Successfully funded 5.0 BTC! TXID: ${res.txid.slice(0, 16)}...`);
      await loadData();
      setTimeout(() => setFundSuccess(null), 5000);
    } catch (err: any) {
      alert(err.message || 'Funding failed');
    } finally {
      setIsFunding(false);
    }
  };

  const handleCreateWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedSignerIds.length < threshold) {
      setCreateError(`Selected signers (${selectedSignerIds.length}) cannot be less than threshold (${threshold})`);
      return;
    }
    setIsCreating(true);
    setCreateError(null);
    try {
      await api.createTreasury(walletName, threshold, selectedSignerIds);
      setShowCreateModal(false);
      setWalletName('');
      await loadData();
    } catch (err: any) {
      setCreateError(err.message || 'Wallet creation failed');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <AppLayout>
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#00F0FF]/15">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Multisig Treasury Wallets</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono neon-badge-cyan">
              P2WSH SEGWIT
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure signing policies, manage public keys, and inspect on-chain multisig parameters
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleFund}
            disabled={isFunding || !currentWallet}
            className="px-4 py-2 rounded-xl neon-btn-emerald disabled:opacity-50 text-xs font-black flex items-center gap-2 transition"
          >
            {isFunding ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#030712]" />
                Mining & Depositing...
              </>
            ) : (
              <>
                <ArrowDownToLine className="w-3.5 h-3.5 text-[#030712]" />
                Deposit 5.0 BTC (Regtest)
              </>
            )}
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 rounded-xl neon-btn-primary text-xs font-black flex items-center gap-2 transition"
          >
            <Plus className="w-3.5 h-3.5 text-[#030712]" />
            New Treasury Policy
          </button>
        </div>
      </div>

      {fundSuccess && (
        <div className="p-3.5 rounded-xl bg-[#00FF9D]/10 border border-[#00FF9D]/40 text-xs text-[#00FF9D] flex items-center gap-2 shadow-[0_0_15px_rgba(0,255,157,0.2)]">
          <ShieldCheck className="w-4 h-4 text-[#00FF9D]" />
          <span className="font-mono font-semibold">{fundSuccess}</span>
        </div>
      )}

      {/* Main Wallet Card */}
      {currentWallet ? (
        <div className="p-6 rounded-2xl neon-card space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-lg font-black text-white tracking-wide">{currentWallet.wallet_name}</span>
                <span className="px-2.5 py-0.5 text-xs font-bold rounded-full neon-badge-cyan">
                  {currentWallet.threshold}-of-{currentWallet.total_signers} Multisig
                </span>
                <span className="px-2.5 py-0.5 text-xs font-bold rounded-full neon-badge-emerald uppercase">
                  {currentWallet.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">BIP-141 Native SegWit P2WSH output script descriptor</p>
            </div>

            <div className="text-right">
              <div className="text-3xl font-mono font-black text-[#00F0FF] drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">
                {currentWallet.balance_btc.toFixed(4)} <span className="text-slate-400 text-sm">BTC</span>
              </div>
              <div className="text-xs font-mono text-slate-400">
                {currentWallet.balance_satoshis.toLocaleString()} satoshis
              </div>
            </div>
          </div>

          {/* Address Box with Neon Highlighting */}
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-[#00F0FF]" />
              Bitcoin Multisig Deposit Address
            </span>
            <div className="p-4 rounded-xl bg-[#030712] border border-[#00F0FF]/30 shadow-[inset_0_2px_10px_rgba(0,0,0,0.8)] flex items-center justify-between gap-3">
              <span className="font-mono text-xs text-[#00F0FF] break-all select-all font-bold drop-shadow-[0_0_6px_rgba(0,240,255,0.4)]">
                {currentWallet.address}
              </span>
              <button
                onClick={handleCopyAddress}
                className="px-3 py-1.5 rounded-lg bg-[#070D1E] hover:bg-[#00F0FF]/20 border border-[#00F0FF]/40 text-xs text-white flex items-center gap-1.5 transition shrink-0 shadow-[0_0_10px_rgba(0,240,255,0.2)]"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[#00FF9D]" /> : <Copy className="w-3.5 h-3.5 text-[#00F0FF]" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Scripts / Descriptor */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-[#030712] border border-slate-800 space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">Output Script Descriptor</span>
              <div className="font-mono text-[11px] text-cyan-300 break-all bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                {currentWallet.descriptor || 'wsh(sortedmulti(...))'}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-[#030712] border border-slate-800 space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">Witness Redeem Script Hex</span>
              <div className="font-mono text-[11px] text-purple-300 break-all bg-slate-950 p-3 rounded-lg border border-slate-800/80 truncate">
                {currentWallet.redeem_script || '5221...53ae'}
              </div>
            </div>
          </div>

          {/* Assigned Signers Table */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#00FF9D] shadow-[0_0_6px_#00FF9D]"></span>
                Configured Custodians ({currentWallet.signers.length})
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Mandates <strong className="text-[#00F0FF]">{currentWallet.threshold}</strong> valid signatures to broadcast
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px] font-mono">
                    <th className="pb-2.5 font-semibold">Signer Label</th>
                    <th className="pb-2.5 font-semibold">Authorized Custodian</th>
                    <th className="pb-2.5 font-semibold">Compressed Public Key (Hex)</th>
                    <th className="pb-2.5 font-semibold text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {currentWallet.signers.map(s => (
                    <tr key={s.signer_id} className="hover:bg-[#00F0FF]/5 transition">
                      <td className="py-3 font-bold text-white">{s.label}</td>
                      <td className="py-3 text-slate-300">{s.user_name}</td>
                      <td className="py-3 font-mono text-[#00F0FF] text-[11px] truncate max-w-xs">{s.public_key}</td>
                      <td className="py-3 text-right">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold neon-badge-emerald uppercase">
                          ACTIVE
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-12 text-center rounded-2xl neon-card text-slate-500">
          No treasury wallets configured yet. Click &apos;New Treasury Policy&apos; above.
        </div>
      )}

      {/* Create Wallet Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl bg-[#070D1E] border border-[#00F0FF]/40 shadow-[0_20px_60px_rgba(0,0,0,0.9)] p-6 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-[#00F0FF]" />
                Deploy Multisig Treasury Policy
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-white text-xs">✕</button>
            </div>

            {createError && (
              <div className="p-3 rounded-xl bg-[#FF1E56]/15 border border-[#FF1E56]/40 text-xs text-[#FF1E56] flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-[#FF1E56] shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateWallet} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Treasury Wallet Name</label>
                <input
                  type="text"
                  required
                  value={walletName}
                  onChange={e => setWalletName(e.target.value)}
                  placeholder="e.g. Operations Reserve Vault"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Signing Threshold (M required of N)</label>
                <select
                  value={threshold}
                  onChange={e => setThreshold(parseInt(e.target.value))}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] transition"
                >
                  <option value={1}>1-of-N (Any single signer)</option>
                  <option value={2}>2-of-N (Corporate standard)</option>
                  <option value={3}>3-of-N (High assurance)</option>
                  <option value={4}>4-of-N (Executive quorum)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Select Custodians to Assign</label>
                <div className="max-h-48 overflow-y-auto space-y-2 p-2 rounded-xl bg-[#030712] border border-slate-800">
                  {signersList.map(s => {
                    const isSelected = selectedSignerIds.includes(s.id);
                    return (
                      <label
                        key={s.id}
                        className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition ${
                          isSelected ? 'bg-[#00F0FF]/10 border border-[#00F0FF]/40' : 'hover:bg-slate-900'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {
                              if (isSelected) {
                                setSelectedSignerIds(selectedSignerIds.filter(id => id !== s.id));
                              } else {
                                setSelectedSignerIds([...selectedSignerIds, s.id]);
                              }
                            }}
                            className="rounded border-slate-700 bg-slate-900 text-[#00F0FF] focus:ring-0"
                          />
                          <div>
                            <span className="font-semibold text-white">{s.label}</span>
                            <span className="text-[10px] text-slate-400 ml-2">({s.user_name})</span>
                          </div>
                        </div>
                        <span className="font-mono text-[10px] text-slate-500 truncate max-w-[120px]">
                          {s.public_key.slice(0, 16)}...
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-4 py-2 rounded-xl neon-btn-primary text-xs font-black flex items-center gap-2 transition"
                >
                  {isCreating ? <Loader2 className="w-3.5 h-3.5 animate-spin text-[#030712]" /> : <ShieldCheck className="w-3.5 h-3.5 text-[#030712]" />}
                  Deploy Multisig Address
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
