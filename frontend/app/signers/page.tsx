'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { api } from '@/lib/api';
import {
  KeyRound, Plus, ShieldCheck, Copy, Check,
  Cpu, HardDrive, RefreshCw, Loader2, AlertCircle, Zap
} from 'lucide-react';

export default function SignersPage() {
  const [signers, setSigners] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Key Generator State
  const [generatedKey, setGeneratedKey] = useState<{
    private_key: string;
    public_key: string;
    fingerprint: string;
    derivation_path: string;
  } | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [newSignerLabel, setNewSignerLabel] = useState<string>('Backup Custody HSM');
  const [regSuccess, setRegSuccess] = useState<string | null>(null);

  const loadSigners = async () => {
    try {
      const list = await api.getSigners();
      setSigners(list);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSigners();
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleGenerateKey = async () => {
    setIsGenerating(true);
    try {
      const kp = await api.generateKeypair();
      setGeneratedKey(kp);
    } catch (err: any) {
      alert(err.message || 'Key generation failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegisterGeneratedKey = async () => {
    if (!generatedKey) return;
    try {
      await api.registerSigner(
        newSignerLabel,
        generatedKey.public_key,
        generatedKey.fingerprint,
        generatedKey.derivation_path
      );
      setRegSuccess(`Signer '${newSignerLabel}' successfully registered!`);
      setGeneratedKey(null);
      await loadSigners();
      setTimeout(() => setRegSuccess(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Registration failed');
    }
  };

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#00F0FF]/15">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white tracking-tight">Signer Management & Public Keys</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono neon-badge-cyan">
              SECP256K1
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage authorized signers, verify secp256k1 public keys, and inspect hardware security modules
          </p>
        </div>

        <button
          onClick={handleGenerateKey}
          disabled={isGenerating}
          className="px-4 py-2 rounded-xl neon-btn-primary disabled:opacity-50 text-xs font-black flex items-center gap-2 transition"
        >
          {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin text-[#030712]" /> : <KeyRound className="w-3.5 h-3.5 text-[#030712]" />}
          Generate Secp256k1 Keypair
        </button>
      </div>

      {regSuccess && (
        <div className="p-3.5 rounded-xl bg-[#00FF9D]/10 border border-[#00FF9D]/40 text-xs text-[#00FF9D] flex items-center gap-2 shadow-[0_0_15px_rgba(0,255,157,0.2)]">
          <ShieldCheck className="w-4 h-4 text-[#00FF9D]" />
          <span>{regSuccess}</span>
        </div>
      )}

      {/* Generated Keypair Inspection Box */}
      {generatedKey && (
        <div className="p-6 rounded-2xl neon-card space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-[#00F0FF] flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#00F0FF]" />
              Fresh Secp256k1 Keypair Generated
            </span>
            <button onClick={() => setGeneratedKey(null)} className="text-xs text-slate-400 hover:text-white">✕</button>
          </div>

          <div className="grid md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="space-y-1">
              <span className="text-slate-400 font-sans text-[11px]">Compressed Public Key (Hex):</span>
              <div className="p-3 rounded-xl bg-[#030712] border border-[#00F0FF]/30 text-[#00F0FF] break-all select-all font-bold">
                {generatedKey.public_key}
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-slate-400 font-sans text-[11px]">Master Fingerprint & Derivation:</span>
              <div className="p-3 rounded-xl bg-[#030712] border border-slate-800 text-slate-300 flex justify-between">
                <span>Fingerprint: <strong className="text-white">{generatedKey.fingerprint}</strong></span>
                <span className="text-[#A855F7] font-bold">{generatedKey.derivation_path}</span>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-[#FFB800]/10 border border-[#FFB800]/40 text-xs text-[#FFB800] flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-[#FFB800] shrink-0 mt-0.5" />
            <div>
              <strong className="text-white">Signer Key Security Rule:</strong> Private keys are never stored in the application database.
              Store this private key securely in your hardware signer or password manager:
              <div className="font-mono text-[10px] text-amber-200 mt-1.5 break-all bg-[#030712] p-2.5 rounded-lg border border-[#FFB800]/30 select-all">
                {generatedKey.private_key}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <input
              type="text"
              value={newSignerLabel}
              onChange={e => setNewSignerLabel(e.target.value)}
              placeholder="Signer Device Label"
              className="px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs w-64 focus:outline-none focus:border-[#00F0FF]"
            />
            <button
              onClick={handleRegisterGeneratedKey}
              className="px-4 py-2.5 rounded-xl neon-btn-primary text-xs font-black transition"
            >
              Register Public Key to Organization
            </button>
          </div>
        </div>
      )}

      {/* Signers Directory */}
      <div className="p-6 rounded-2xl neon-card space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00F0FF] shadow-[0_0_8px_#00F0FF]"></span>
              Active Custodians & Hardware Keys
            </h2>
            <p className="text-xs text-slate-400">Registered public keys authorized to sign corporate Bitcoin PSBTs</p>
          </div>
          <span className="text-xs font-mono text-[#00F0FF] font-bold">{signers.length} keys active</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px] font-mono">
                <th className="pb-3 font-semibold">Device / Label</th>
                <th className="pb-3 font-semibold">Authorized Custodian</th>
                <th className="pb-3 font-semibold">Fingerprint</th>
                <th className="pb-3 font-semibold">Derivation Path</th>
                <th className="pb-3 font-semibold">Compressed Public Key (Hex)</th>
                <th className="pb-3 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {signers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                    No signers registered yet.
                  </td>
                </tr>
              ) : (
                signers.map(s => (
                  <tr key={s.id} className="hover:bg-[#00F0FF]/5 transition">
                    <td className="py-3.5 font-bold text-white flex items-center gap-2 font-sans">
                      <HardDrive className="w-3.5 h-3.5 text-[#00F0FF]" />
                      {s.label}
                    </td>
                    <td className="py-3.5 text-slate-300 font-sans">{s.user_name}</td>
                    <td className="py-3.5 text-slate-300 font-bold">{s.fingerprint || '---'}</td>
                    <td className="py-3.5 text-slate-400">{s.derivation_path || "m/48'/1'/0'/2'"}</td>
                    <td className="py-3.5 text-[#00F0FF] text-[11px] truncate max-w-xs">
                      <div className="flex items-center gap-2">
                        <span className="truncate">{s.public_key}</span>
                        <button
                          onClick={() => handleCopy(s.public_key, s.id.toString())}
                          className="text-slate-500 hover:text-white shrink-0"
                          title="Copy public key"
                        >
                          {copiedKey === s.id.toString() ? (
                            <Check className="w-3 h-3 text-[#00FF9D]" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3.5 text-right font-sans">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold neon-badge-emerald uppercase">
                        {s.status}
                      </span>
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
