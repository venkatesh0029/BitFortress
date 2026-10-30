'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { TreasuryWallet, SpendingPolicy } from '@/lib/types';
import {
  Send, AlertTriangle, CheckCircle2, ShieldCheck,
  ArrowRight, Loader2, Info, ArrowLeft, Zap
} from 'lucide-react';
import Link from 'next/link';

export default function ProposeTransactionPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [wallets, setWallets] = useState<TreasuryWallet[]>([]);
  const [policy, setPolicy] = useState<SpendingPolicy | null>(null);
  const [selectedWalletId, setSelectedWalletId] = useState<number | ''>('');
  const [destination, setDestination] = useState<string>('');
  const [amountBtc, setAmountBtc] = useState<string>('0.25');
  const [amountSats, setAmountSats] = useState<number>(25_000_000);
  const [feeSats, setFeeSats] = useState<number>(1000);
  const [description, setDescription] = useState<string>('Corporate Server Infrastructure Renewal Q4');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchContext = async () => {
      try {
        const [wList, p] = await Promise.all([
          api.getTreasuries(),
          api.getPolicy().catch(() => null)
        ]);
        setWallets(wList);
        if (wList.length > 0) {
          setSelectedWalletId(wList[0].id);
        }
        setPolicy(p);
      } catch (e) {
        console.error(e);
      }
    };
    fetchContext();
  }, []);

  const handleBtcChange = (val: string) => {
    setAmountBtc(val);
    const num = parseFloat(val);
    if (!isNaN(num) && num > 0) {
      setAmountSats(Math.round(num * 100_000_000));
    } else {
      setAmountSats(0);
    }
  };

  const handleSatsChange = (val: number) => {
    setAmountSats(val);
    setAmountBtc((val / 100_000_000).toFixed(8));
  };

  const selectedWallet = wallets.find(w => w.id === selectedWalletId);
  const isOverPerTxLimit = policy ? amountSats > policy.per_transaction_limit : false;
  const isOverBalance = selectedWallet ? amountSats + feeSats > selectedWallet.balance_satoshis : false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWalletId) {
      setErrorMsg('Please select a treasury wallet');
      return;
    }
    if (amountSats <= 0) {
      setErrorMsg('Amount must be greater than zero');
      return;
    }
    if (isOverBalance) {
      setErrorMsg('Amount plus fee exceeds treasury wallet reserve balance');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const proposal = await api.proposeTransaction(
        selectedWalletId as number,
        destination.trim(),
        amountSats,
        feeSats,
        description.trim()
      );
      router.push(`/approvals?id=${proposal.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit proposal');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AppLayout>
      <div className="flex items-center gap-3 pb-2 border-b border-[#00F0FF]/15">
        <Link href="/transactions" className="p-2 rounded-xl bg-[#070D1E] hover:bg-[#00F0FF]/10 text-slate-400 hover:text-[#00F0FF] border border-slate-800 transition">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Propose Corporate Payment</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono neon-badge-cyan">
              PSBT CONSTRUCTOR
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Initializes an unsigned PSBT for review and signature by authorized treasury signers
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Form Column */}
        <div className="lg:col-span-2 p-6 rounded-2xl neon-card space-y-6">
          {errorMsg && (
            <div className="p-4 rounded-xl bg-[#FF1E56]/15 border border-[#FF1E56]/40 text-xs text-[#FF1E56] flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-[#FF1E56] shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Wallet Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Source Treasury Wallet</label>
              <select
                value={selectedWalletId}
                onChange={e => setSelectedWalletId(parseInt(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.25)] transition font-mono"
              >
                {wallets.map(w => (
                  <option key={w.id} value={w.id}>
                    {w.wallet_name} ({w.balance_btc.toFixed(4)} BTC available • {w.threshold}-of-{w.total_signers} Quorum)
                  </option>
                ))}
              </select>
            </div>

            {/* Destination Address */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Destination Bitcoin Address</label>
              <input
                type="text"
                required
                value={destination}
                onChange={e => setDestination(e.target.value)}
                placeholder="e.g. bcrt1q... or 2..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-[#00F0FF] font-mono text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.25)] transition"
              />
              <p className="text-[11px] text-slate-500 mt-1 font-mono">Recipient Bitcoin address on Regtest/Testnet</p>
            </div>

            {/* Amount Dual Converter */}
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Amount in BTC</label>
                <div className="relative">
                  <input
                    type="number"
                    step="0.00000001"
                    min="0.00001"
                    required
                    value={amountBtc}
                    onChange={e => handleBtcChange(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white font-mono text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.25)] transition pr-12 font-bold"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs font-bold text-[#00F0FF]">BTC</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Amount in Satoshis</label>
                <div className="relative">
                  <input
                    type="number"
                    required
                    value={amountSats}
                    onChange={e => handleSatsChange(parseInt(e.target.value) || 0)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white font-mono text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.25)] transition pr-12 font-bold"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs font-bold text-[#FFB800]">sats</span>
                </div>
              </div>
            </div>

            {/* Fee & Justification */}
            <div className="grid sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Network Mining Fee</label>
                <input
                  type="number"
                  value={feeSats}
                  onChange={e => setFeeSats(parseInt(e.target.value) || 1000)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white font-mono text-xs focus:outline-none focus:border-[#00F0FF] transition font-bold"
                />
                <span className="text-[10px] text-slate-500 mt-1 block font-mono">1,000 sats (~0.00001 BTC)</span>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Corporate Justification / Memo</label>
                <input
                  type="text"
                  required
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="e.g. Quarterly Treasury Rebalancing"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] transition"
                />
                <span className="text-[10px] text-slate-500 mt-1 block font-mono">Preserved in immutable audit trail</span>
              </div>
            </div>

            {/* Policy Check Alert */}
            {isOverPerTxLimit && (
              <div className="p-4 rounded-xl bg-[#FFB800]/15 border border-[#FFB800]/40 text-xs text-[#FFB800] flex items-start gap-2 shadow-[0_0_15px_rgba(255,184,0,0.15)]">
                <AlertTriangle className="w-4 h-4 text-[#FFB800] shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-white">Exceeds Per-Transaction Policy Limit</div>
                  <div>
                    This amount ({amountBtc} BTC) exceeds the active corporate limit of {policy?.per_tx_btc} BTC. The backend policy engine will reject this proposal without an administrator override.
                  </div>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || isOverBalance}
              className="w-full py-3.5 px-4 rounded-xl neon-btn-primary text-xs font-black flex items-center justify-center gap-2 transition"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-[#030712]" />
                  Generating PSBT via Bitcoin Core...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 text-[#030712]" />
                  Construct PSBT & Dispatch for Quorum Signatures
                </>
              )}
            </button>
          </form>
        </div>

        {/* Summary & Review Sidebar */}
        <div className="p-6 rounded-2xl neon-card space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-[#00F0FF]" />
              Pre-flight Quorum Assessment
            </h3>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400 font-sans">Quorum Threshold:</span>
                <span className="font-bold text-[#00F0FF]">
                  {selectedWallet ? `${selectedWallet.threshold}-of-${selectedWallet.total_signers}` : '2-of-3'}
                </span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400 font-sans">Disbursement:</span>
                <span className="font-bold text-white text-[13px]">{amountBtc} BTC</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400 font-sans">Miner Fee:</span>
                <span className="text-slate-300">{(feeSats / 100_000_000).toFixed(8)} BTC</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400 font-sans">Policy Limit:</span>
                <span className="text-[#00FF9D] font-bold">{policy ? `${policy.per_tx_btc} BTC` : '0.50 BTC'}</span>
              </div>

              <div className="flex justify-between py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400 font-sans">Mandatory Signatures:</span>
                <span className="font-bold text-[#FFB800]">
                  {selectedWallet?.threshold || 2} Custodians
                </span>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-[#030712] border border-[#00F0FF]/30 text-[11px] text-slate-400 space-y-1.5 shadow-[0_0_15px_rgba(0,240,255,0.1)]">
            <div className="font-bold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-[#00F0FF]" />
              BIP-174 Guarantees
            </div>
            <div>
              Creating a proposal builds a BIP-174 Partially Signed Bitcoin Transaction. Funds remain locked until the threshold of valid ECDSA DER signatures is met.
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
