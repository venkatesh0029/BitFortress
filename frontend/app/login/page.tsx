'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { DemoUser } from '@/lib/types';
import {
  Shield, KeyRound, ArrowRight, UserCheck, AlertCircle,
  Loader2, CheckCircle2, Lock, Zap
} from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, quickLogin, demoUsers } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('password123');
  const [fullName, setFullName] = useState('');
  const [orgName, setOrgName] = useState('Acme Global Treasury');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);
    try {
      if (isRegister) {
        await api.register(email, fullName, password, orgName);
        await login(email, password);
      } else {
        await login(email, password);
      }
      router.push('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = async (demo: DemoUser) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await quickLogin(demo);
      router.push('/dashboard');
    } catch (err: any) {
      setErrorMsg(err.message || 'Quick login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col justify-center items-center p-6 selection:bg-[#00F0FF] selection:text-black">
      {/* Brand */}
      <div className="mb-8 text-center space-y-2">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-[#00F0FF] to-[#A855F7] p-[1.5px] shadow-[0_0_25px_rgba(0,240,255,0.4)] mb-2">
          <div className="w-full h-full bg-[#030712] rounded-[14px] flex items-center justify-center">
            <Shield className="w-7 h-7 text-[#00F0FF] drop-shadow-[0_0_10px_#00F0FF]" />
          </div>
        </div>
        <h1 className="text-3xl font-black text-white tracking-tight">
          Satoshi<span className="text-[#00F0FF] drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">Guard</span>
        </h1>
        <p className="text-xs text-slate-400 font-mono">INSTITUTIONAL MULTISIG AUTHORIZATION PROTOCOL</p>
      </div>

      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-6 items-stretch">
        {/* Left: 1-Click Persona Simulator */}
        <div className="p-6 rounded-2xl neon-card flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/30 shadow-[0_0_10px_rgba(0,240,255,0.2)]">
                <Zap className="w-4 h-4" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-white">Instant Demo Personas</h3>
                <p className="text-xs text-slate-400">1-Click role simulation for multi-signer approvals</p>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              {demoUsers.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500">
                  <Loader2 className="w-4 h-4 animate-spin mx-auto mb-2 text-[#00F0FF]" />
                  Loading demo profiles...
                </div>
              ) : (
                demoUsers.map(du => (
                  <button
                    key={du.id}
                    onClick={() => handleQuickLogin(du)}
                    disabled={isLoading}
                    className="w-full text-left p-3 rounded-xl bg-[#030712]/70 hover:bg-[#00F0FF]/10 border border-slate-800/80 hover:border-[#00F0FF]/50 transition flex items-center justify-between group shadow-sm hover:shadow-[0_0_15px_rgba(0,240,255,0.2)]"
                  >
                    <div>
                      <div className="text-xs font-bold text-white group-hover:text-[#00F0FF] transition">
                        {du.full_name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">{du.email}</div>
                    </div>
                    <div className="text-right">
                      <span className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider neon-badge-cyan">
                        {du.role}
                      </span>
                      {du.has_signer_key && (
                        <div className="text-[9px] text-[#00FF9D] font-mono font-bold mt-1 drop-shadow-[0_0_6px_rgba(0,255,157,0.5)]">
                          KEY READY
                        </div>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 text-[10px] text-slate-500 font-mono flex items-center justify-between">
            <span>PRE-LOADED HSM KEYS</span>
            <span className="text-[#00F0FF]">1-CLICK AUTH</span>
          </div>
        </div>

        {/* Right: Custom Credentials Form */}
        <div className="p-6 rounded-2xl neon-card flex flex-col justify-between">
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <button
                type="button"
                onClick={() => { setIsRegister(false); setErrorMsg(null); }}
                className={`text-sm font-bold pb-1 transition ${
                  !isRegister ? 'text-[#00F0FF] border-b-2 border-[#00F0FF] drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]' : 'text-slate-400 hover:text-white'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setIsRegister(true); setErrorMsg(null); }}
                className={`text-sm font-bold pb-1 transition ${
                  isRegister ? 'text-[#00F0FF] border-b-2 border-[#00F0FF] drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]' : 'text-slate-400 hover:text-white'
                }`}
              >
                Create Treasury Org
              </button>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-xl bg-[#FF1E56]/15 border border-[#FF1E56]/40 text-xs text-[#FF1E56] flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-[#FF1E56]" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {isRegister && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Organization Name</label>
                    <input
                      type="text"
                      required
                      value={orgName}
                      onChange={e => setOrgName(e.target.value)}
                      placeholder="e.g. Acme Corp Treasury"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] transition"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={e => setFullName(e.target.value)}
                      placeholder="Jane Doe"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] transition"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Work Email</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@satoshiguard.io"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#030712] border border-slate-800 text-white text-xs focus:outline-none focus:border-[#00F0FF] focus:shadow-[0_0_15px_rgba(0,240,255,0.3)] transition"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 rounded-xl neon-btn-primary text-xs font-black flex items-center justify-center gap-2 transition"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-[#030712]" />
                    Authenticating...
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5 text-[#030712]" />
                    {isRegister ? 'Register & Initialize' : 'Sign In to Treasury'}
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="pt-4 border-t border-slate-800 text-center">
            <Link href="/" className="text-xs text-slate-500 hover:text-[#00F0FF] transition font-mono">
              ← Return to Product Overview
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
