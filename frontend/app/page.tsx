'use client';

import React from 'react';
import Link from 'next/link';
import {
  Shield, CheckCircle2, Lock, Cpu, ArrowRight,
  KeyRound, Users, ShieldAlert, Layers, Zap
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col selection:bg-[#00F0FF] selection:text-black">
      {/* Header */}
      <header className="border-b border-[#00F0FF]/15 bg-[#030712]/90 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00F0FF] via-blue-600 to-[#A855F7] p-[1.5px] shadow-[0_0_20px_rgba(0,240,255,0.4)]">
              <div className="w-full h-full bg-[#030712] rounded-[10px] flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#00F0FF] drop-shadow-[0_0_8px_#00F0FF]" />
              </div>
            </div>
            <div>
              <span className="text-xl font-black tracking-tight text-white">
                Bit<span className="text-[#00F0FF] drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">Fortress</span>
              </span>
              <span className="ml-2 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full neon-badge-cyan">
                NEON PROTOCOL
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-xs font-semibold text-slate-300 hover:text-[#00F0FF] px-3 py-2 rounded-xl hover:bg-slate-900 transition"
            >
              Sign In
            </Link>
            <Link
              href="/dashboard"
              className="text-xs font-black text-[#030712] neon-btn-primary px-4 py-2 rounded-xl transition flex items-center gap-2"
            >
              Launch Platform
              <ArrowRight className="w-4 h-4 text-[#030712]" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-24 pb-28 overflow-hidden border-b border-[#00F0FF]/10">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-[#00F0FF]/10 blur-[150px] rounded-full pointer-events-none" />
        <div className="absolute top-1/2 right-1/4 w-[400px] h-[300px] bg-[#A855F7]/10 blur-[130px] rounded-full pointer-events-none" />

        <div className="max-w-5xl mx-auto px-6 text-center space-y-7 relative z-10">
          <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full neon-badge-cyan text-xs font-bold font-mono">
            <span className="w-2 h-2 rounded-full bg-[#00F0FF] animate-ping" />
            <span>BITCOIN CORE REGTEST • BIP-174 MULTISIG PSBT PROTOCOL</span>
          </div>

          <h1 className="text-4xl sm:text-7xl font-black tracking-tight text-white leading-tight">
            Institutional Bitcoin Treasury with <span className="bg-gradient-to-r from-[#00F0FF] via-cyan-300 to-[#A855F7] bg-clip-text text-transparent drop-shadow-[0_0_35px_rgba(0,240,255,0.4)]">Multi-Signer Quorum</span>
          </h1>

          <p className="max-w-2xl mx-auto text-base sm:text-lg text-slate-300 leading-relaxed font-light">
            Eliminate single-point-of-failure key risk with cryptographic quorum policies.
            Propose, review, cryptographically sign, and broadcast Partially Signed Bitcoin Transactions directly through Bitcoin Core.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-7 py-4 rounded-xl neon-btn-primary text-[#030712] font-black text-sm transition flex items-center justify-center gap-2"
            >
              Enter Live Treasury
              <ArrowRight className="w-4 h-4 text-[#030712]" />
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto px-7 py-4 rounded-xl bg-[#070D1E] hover:bg-[#0C152B] text-slate-200 border border-[#00F0FF]/30 hover:border-[#00F0FF]/60 font-bold text-sm transition shadow-[0_0_20px_rgba(0,0,0,0.6)] flex items-center justify-center gap-2"
            >
              1-Click Persona Simulator
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="py-24 max-w-7xl mx-auto px-6">
        <div className="text-center space-y-2 mb-16">
          <p className="text-xs font-black uppercase tracking-widest text-[#00F0FF] drop-shadow-[0_0_8px_#00F0FF]">
            DEFENSE-IN-DEPTH ARCHITECTURE
          </p>
          <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">Institutional Quorum Controls</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="p-7 rounded-2xl neon-card space-y-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#00F0FF]/10 text-[#00F0FF] flex items-center justify-center border border-[#00F0FF]/30 shadow-[0_0_15px_rgba(0,240,255,0.3)]">
              <KeyRound className="w-6 h-6 drop-shadow-[0_0_8px_#00F0FF]" />
            </div>
            <h3 className="text-lg font-bold text-white">M-of-N Quorum Policies</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enforce configurable signing thresholds like 2-of-3 or 3-of-5. Funds cannot be moved without independent cryptographically verified signatures.
            </p>
          </div>

          <div className="p-7 rounded-2xl neon-card-purple space-y-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#A855F7]/10 text-[#C084FC] flex items-center justify-center border border-[#A855F7]/30 shadow-[0_0_15px_rgba(168,85,247,0.3)]">
              <Layers className="w-6 h-6 drop-shadow-[0_0_8px_#C084FC]" />
            </div>
            <h3 className="text-lg font-bold text-white">PSBT Standard Protocol</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              BIP-174 Partially Signed Bitcoin Transactions ensure signers verify inputs, destination, and fee parameters independently before signing.
            </p>
          </div>

          <div className="p-7 rounded-2xl neon-card-emerald space-y-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#00FF9D]/10 text-[#00FF9D] flex items-center justify-center border border-[#00FF9D]/30 shadow-[0_0_15px_rgba(0,255,157,0.3)]">
              <ShieldAlert className="w-6 h-6 drop-shadow-[0_0_8px_#00FF9D]" />
            </div>
            <h3 className="text-lg font-bold text-white">Spending Limit Engine</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Mandatory per-transaction caps and 24-hour rolling daily velocity limits. Violations are automatically blocked and logged to the audit log.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 border-t border-[#00F0FF]/15 text-center text-xs text-slate-500 font-mono">
        <p>BitFortress • Professional Bitcoin Multi-Sig Protocol • Next.js & FastAPI on Bitcoin Core Regtest</p>
      </footer>
    </div>
  );
}
