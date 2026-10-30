'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { TransactionProposal, DemoUser } from '@/lib/types';
import {
  CheckSquare, ShieldAlert, KeyRound, CheckCircle2,
  XCircle, Copy, Check, ArrowRight, Loader2, Send,
  Cpu, Lock, AlertTriangle, Eye, ShieldCheck, Zap
} from 'lucide-react';

export default function ApprovalsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500 font-mono">Loading approvals...</div>}>
      <ApprovalsContent />
    </Suspense>
  );
}

function ApprovalsContent() {
  const searchParams = useSearchParams();
  const highlightedId = searchParams.get('id');
  const { user, demoUsers } = useAuth();
  const [proposals, setProposals] = useState<TransactionProposal[]>([]);
  const [selectedProposal, setSelectedProposal] = useState<TransactionProposal | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSigning, setIsSigning] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [rejectionReason, setRejectionReason] = useState<string>('');
  const [showRejectModal, setShowRejectModal] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [copiedPsbt, setCopiedPsbt] = useState<boolean>(false);

  const loadProposals = async () => {
    try {
      const list = await api.getTransactions(undefined, 'PENDING');
      setProposals(list);

      if (highlightedId) {
        const found = list.find(p => p.id === parseInt(highlightedId));
        if (found) {
          const detail = await api.getTransaction(found.id);
          setSelectedProposal(detail);
        }
      } else if (list.length > 0 && !selectedProposal) {
        const detail = await api.getTransaction(list[0].id);
        setSelectedProposal(detail);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProposals();
  }, [highlightedId]);

  const handleSelectProposal = async (p: TransactionProposal) => {
    try {
      const detail = await api.getTransaction(p.id);
      setSelectedProposal(detail);
      setActionSuccess(null);
      setErrorMessage(null);
    } catch (err: any) {
      console.error(err);
    }
  };

  const currentDemoUser = demoUsers.find(du => du.email === user?.email);

  const handleApproveAndSign = async () => {
    if (!selectedProposal) return;
    setIsSigning(true);
    setErrorMessage(null);
    setActionSuccess(null);

    try {
      const res = await api.signProposal(
        selectedProposal.id,
        selectedProposal.current_psbt,
        undefined,
        currentDemoUser ? `${currentDemoUser.signer_label} (${currentDemoUser.full_name})` : `Signer Session`
      );

      if (res.broadcast_info && res.broadcast_info.broadcast) {
        setActionSuccess(
          `Signing threshold reached (${res.approved_count}/${res.threshold})! Finalized and broadcast to Regtest. TXID: ${res.broadcast_info.txid.slice(0, 18)}...`
        );
      } else {
        setActionSuccess(
          `Signature recorded! Quorum progress: ${res.approved_count}/${res.threshold} signatures collected.`
        );
      }

      await loadProposals();
      const updatedDetail = await api.getTransaction(selectedProposal.id);
      setSelectedProposal(updatedDetail);
    } catch (err: any) {
      setErrorMessage(err.message || 'Signing failed');
    } finally {
      setIsSigning(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProposal || !rejectionReason.trim()) return;
    setIsRejecting(true);
    setErrorMessage(null);

    try {
      await api.rejectProposal(selectedProposal.id, rejectionReason.trim());
      setShowRejectModal(false);
      setRejectionReason('');
      setActionSuccess(`Proposal #${selectedProposal.id} has been formally rejected. Funds remain safe.`);
      await loadProposals();
      const updatedDetail = await api.getTransaction(selectedProposal.id);
      setSelectedProposal(updatedDetail);
    } catch (err: any) {
      setErrorMessage(err.message || 'Rejection failed');
    } finally {
      setIsRejecting(false);
    }
  };

  const copyPsbt = () => {
    if (!selectedProposal?.current_psbt) return;
    navigator.clipboard.writeText(selectedProposal.current_psbt);
    setCopiedPsbt(true);
    setTimeout(() => setCopiedPsbt(false), 2000);
  };

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#00F0FF]/15">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Signer Authorization Center</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono neon-badge-cyan">
              QUORUM PROTOCOL
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Review partially signed bitcoin transactions (PSBT) and provide authorized cryptographic signatures
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-mono">ACTIVE ROLE:</span>
          <span className="px-2.5 py-1 rounded-full neon-badge-cyan font-bold uppercase font-mono">
            {user?.role || 'SIGNER'}
          </span>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-[#00FF9D]/10 border border-[#00FF9D]/40 text-xs text-[#00FF9D] flex items-start gap-2.5 shadow-[0_0_15px_rgba(0,255,157,0.2)]">
          <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0 mt-0.5" />
          <span className="font-mono font-semibold">{actionSuccess}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-[#FF1E56]/15 border border-[#FF1E56]/40 text-xs text-[#FF1E56] flex items-start gap-2.5 shadow-[0_0_15px_rgba(255,30,86,0.2)]">
          <AlertTriangle className="w-4 h-4 text-[#FF1E56] shrink-0 mt-0.5" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Left Column: Proposals List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Zap className="w-3 h-3 text-[#00F0FF]" />
              Pending Quorum Reviews ({proposals.length})
            </span>
          </div>

          <div className="space-y-2.5 max-h-[700px] overflow-y-auto">
            {proposals.length === 0 ? (
              <div className="p-8 text-center rounded-2xl neon-card text-slate-500 text-xs">
                No pending transaction proposals awaiting signature.
              </div>
            ) : (
              proposals.map(p => {
                const isSelected = selectedProposal?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => handleSelectProposal(p)}
                    className={`p-4 rounded-xl border text-left cursor-pointer transition ${
                      isSelected
                        ? 'bg-[#00F0FF]/10 border-[#00F0FF]/60 shadow-[0_0_20px_rgba(0,240,255,0.25)]'
                        : 'bg-[#070D1E] border-slate-800/80 hover:border-[#00F0FF]/30'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-[#00F0FF] font-black">#{p.id}</span>
                          <span className="text-xs font-bold text-white">{p.description}</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1 font-mono">
                          Destination: {p.destination.slice(0, 16)}...
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-mono font-black text-white">
                          {p.amount_btc.toFixed(4)} <span className="text-[#00F0FF] text-[10px]">BTC</span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          {p.amount_satoshis.toLocaleString()} sats
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800">
                          <div
                            className="bg-gradient-to-r from-[#00F0FF] to-blue-500 h-1.5 rounded-full shadow-[0_0_6px_#00F0FF]"
                            style={{ width: `${Math.min(100, (p.approvals_count / p.threshold) * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-[10px] text-[#00F0FF] font-bold">
                          {p.approvals_count}/{p.threshold} Quorum
                        </span>
                      </div>
                      <span className="text-[10px] font-bold neon-badge-amber uppercase">
                        {p.status}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Signer Review Panel */}
        <div className="lg:col-span-7">
          {selectedProposal ? (
            <div className="p-6 rounded-2xl neon-card space-y-6">
              <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-black text-white">Proposal #{selectedProposal.id}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded-full neon-badge-cyan">
                      {selectedProposal.wallet_name}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1 font-medium">{selectedProposal.description}</p>
                </div>

                <div className="text-right">
                  <div className="text-3xl font-mono font-black text-[#00F0FF] drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">
                    {selectedProposal.amount_btc.toFixed(4)} <span className="text-slate-400 text-sm">BTC</span>
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    Fee: {(selectedProposal.fee_satoshis / 100_000_000).toFixed(8)} BTC
                  </div>
                </div>
              </div>

              {/* Transaction Inspection Parameters */}
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 font-mono">
                  <Zap className="w-3 h-3 text-[#00F0FF]" />
                  Cryptographic Verification Parameters
                </span>

                <div className="p-4 rounded-xl bg-[#030712] border border-slate-800 space-y-2 text-xs font-mono">
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400 font-sans">Recipient Destination:</span>
                    <span className="text-[#00F0FF] break-all select-all font-bold drop-shadow-[0_0_6px_rgba(0,240,255,0.4)]">
                      {selectedProposal.destination}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400 font-sans">Proposer Identity:</span>
                    <span className="text-slate-200 font-sans font-semibold">{selectedProposal.proposer_name}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800/60">
                    <span className="text-slate-400 font-sans">Quorum Threshold:</span>
                    <span className="font-bold text-[#A855F7] font-sans">
                      {selectedProposal.threshold} independent signatures needed
                    </span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-400 font-sans">Signatures Collected:</span>
                    <span className="text-[#00FF9D] font-black text-sm">
                      {selectedProposal.approvals_count} / {selectedProposal.threshold}
                    </span>
                  </div>
                </div>
              </div>

              {/* Accumulated Signatures Timeline */}
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                  Signer Decision Records
                </span>

                <div className="space-y-2">
                  {selectedProposal.approvals && selectedProposal.approvals.length > 0 ? (
                    selectedProposal.approvals.map(app => (
                      <div
                        key={app.id}
                        className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
                          app.decision === 'APPROVED'
                            ? 'bg-[#00FF9D]/10 border-[#00FF9D]/40 text-[#00FF9D]'
                            : 'bg-[#FF1E56]/10 border-[#FF1E56]/40 text-[#FF1E56]'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          {app.decision === 'APPROVED' ? (
                            <CheckCircle2 className="w-4 h-4 text-[#00FF9D] drop-shadow-[0_0_6px_#00FF9D]" />
                          ) : (
                            <XCircle className="w-4 h-4 text-[#FF1E56] drop-shadow-[0_0_6px_#FF1E56]" />
                          )}
                          <div>
                            <div className="font-bold text-white">{app.signer_name}</div>
                            <div className="text-[10px] text-slate-400 font-mono">
                              Key: {app.public_key ? app.public_key.slice(0, 24) + '...' : 'Hardware Key'}
                            </div>
                            {app.rejection_reason && (
                              <div className="text-[11px] text-[#FF1E56] mt-0.5 font-sans">
                                Veto Reason: {app.rejection_reason}
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="text-right text-[10px] text-slate-400 font-mono">
                          {new Date(app.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 text-center text-xs text-slate-500 rounded-xl bg-[#030712] border border-slate-800">
                      No signatures submitted yet. Awaiting initial review.
                    </div>
                  )}
                </div>
              </div>

              {/* Raw PSBT Inspector with Neon Highlighting */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 font-mono">BIP-174 Partially Signed PSBT (Base64)</span>
                  <button
                    onClick={copyPsbt}
                    className="text-xs text-[#00F0FF] hover:underline flex items-center gap-1 font-mono font-bold"
                  >
                    {copiedPsbt ? <Check className="w-3.5 h-3.5 text-[#00FF9D]" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedPsbt ? 'Copied' : 'Copy PSBT'}
                  </button>
                </div>
                <div className="p-3.5 rounded-xl bg-[#030712] border border-slate-800 font-mono text-[10px] text-cyan-300 break-all max-h-24 overflow-y-auto select-all">
                  {selectedProposal.current_psbt || 'cHNidP8BAFICAAAA...'}
                </div>
              </div>

              {/* Action Buttons */}
              {selectedProposal.status === 'PENDING' ? (
                <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center gap-3">
                  <button
                    onClick={() => setShowRejectModal(true)}
                    disabled={isSigning || isRejecting}
                    className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-[#FF1E56]/15 hover:bg-[#FF1E56]/30 border border-[#FF1E56]/50 text-[#FF1E56] text-xs font-bold flex items-center justify-center gap-2 transition"
                  >
                    <XCircle className="w-4 h-4" />
                    Reject Proposal
                  </button>

                  <button
                    onClick={handleApproveAndSign}
                    disabled={isSigning || isRejecting}
                    className="w-full sm:flex-1 px-5 py-3 rounded-xl neon-btn-primary text-xs font-black flex items-center justify-center gap-2 transition"
                  >
                    {isSigning ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-[#030712]" />
                        Verifying Signature & Combining PSBT...
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-4 h-4 text-[#030712]" />
                        Sign PSBT & Authorize ({currentDemoUser?.signer_label || 'Current Custodian'})
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-[#030712] border border-slate-800 text-xs flex items-center justify-between">
                  <span className="text-slate-400 font-mono">FINAL STATE:</span>
                  <span className="font-black text-white uppercase font-mono">{selectedProposal.status}</span>
                  {selectedProposal.txid && (
                    <span className="font-mono text-[#00F0FF] text-[11px] font-bold">
                      TXID: {selectedProposal.txid.slice(0, 16)}...
                    </span>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-16 text-center rounded-2xl neon-card text-slate-500 text-sm">
              Select a proposal from the left panel to review transaction parameters and sign.
            </div>
          )}
        </div>
      </div>

      {/* Rejection Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl bg-[#070D1E] border border-[#FF1E56]/40 shadow-[0_20px_60px_rgba(0,0,0,0.9)] p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-[#FF1E56]" />
                Reject Transaction Proposal
              </h3>
              <button onClick={() => setShowRejectModal(false)} className="text-slate-400 hover:text-white text-xs">✕</button>
            </div>

            <p className="text-xs text-slate-300">
              Rejecting permanently blocks this transaction from being broadcast. You must provide a formal corporate justification reason for the audit trail.
            </p>

            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Rejection Justification</label>
                <textarea
                  required
                  rows={3}
                  value={rejectionReason}
                  onChange={e => setRejectionReason(e.target.value)}
                  placeholder="e.g. Destination address does not match verified vendor invoice..."
                  className="w-full p-3 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#FF1E56] transition"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRejecting}
                  className="px-4 py-2 rounded-xl bg-[#FF1E56] hover:bg-[#FF1E56]/90 text-white text-xs font-black transition flex items-center gap-2 shadow-[0_0_15px_rgba(255,30,86,0.4)]"
                >
                  {isRejecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
