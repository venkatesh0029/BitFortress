'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from './RoleContext';
import { api } from '@/lib/api';
import {
  LayoutDashboard, Vault, Send, CheckSquare, KeyRound,
  History, ShieldAlert, BarChart3, Settings, Pickaxe,
  CheckCircle, Loader2, Zap
} from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isMining, setIsMining] = useState<boolean>(false);
  const [minedSuccess, setMinedSuccess] = useState<string | null>(null);

  useEffect(() => {
    const fetchPending = async () => {
      if (user) {
        try {
          const pending = await api.getPendingApprovals();
          setPendingCount(pending.length);
        } catch {}
      }
    };
    fetchPending();
    const interval = setInterval(fetchPending, 8000);
    return () => clearInterval(interval);
  }, [user]);

  const handleMineBlock = async () => {
    setIsMining(true);
    setMinedSuccess(null);
    try {
      const res = await api.mineBlocks(1);
      setMinedSuccess(`Block #${res.new_height} mined!`);
      setTimeout(() => setMinedSuccess(null), 3000);
    } catch (err: any) {
      console.error(err);
    } finally {
      setIsMining(false);
    }
  };

  const navItems = [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Treasury Wallets', href: '/treasury', icon: Vault },
    { label: 'Propose Transfer', href: '/transactions/propose', icon: Send },
    {
      label: 'Signer Approvals',
      href: '/approvals',
      icon: CheckSquare,
      badge: pendingCount > 0 ? pendingCount : undefined
    },
    { label: 'Signer Management', href: '/signers', icon: KeyRound },
    { label: 'Transaction History', href: '/transactions', icon: History },
    { label: 'Security Center', href: '/security', icon: ShieldAlert },
    { label: 'Analytics', href: '/analytics', icon: BarChart3 },
    { label: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 border-r border-[#00F0FF]/15 bg-[#030712]/90 flex flex-col justify-between p-4 shrink-0 shadow-[4px_0_30px_rgba(0,0,0,0.7)] backdrop-blur-xl">
      <div className="space-y-6">
        <div className="px-3 py-1 flex items-center justify-between">
          <p className="text-[10px] font-black uppercase tracking-widest text-[#00F0FF] drop-shadow-[0_0_8px_rgba(0,240,255,0.4)]">
            Treasury Navigation
          </p>
          <Zap className="w-3 h-3 text-[#00F0FF]" />
        </div>

        <nav className="space-y-1.5">
          {navItems.map(item => {
            const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? 'bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/40 shadow-[0_0_20px_-3px_rgba(0,240,255,0.3)] font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900/60 hover:border-slate-800 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#00F0FF] drop-shadow-[0_0_8px_rgba(0,240,255,0.7)]' : 'text-slate-500'}`} />
                  <span className={isActive ? 'text-white' : ''}>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-[10px] font-black rounded-full bg-[#FFB800]/20 text-[#FFB800] border border-[#FFB800]/50 shadow-[0_0_10px_#FFB800] animate-pulse">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Regtest Interactive Miner Box */}
      <div className="p-4 rounded-2xl neon-card space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold text-white flex items-center gap-1.5">
            <Pickaxe className="w-3.5 h-3.5 text-[#00F0FF] drop-shadow-[0_0_6px_#00F0FF]" />
            Regtest Simulator
          </span>
          <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded neon-badge-cyan">Local Node</span>
        </div>
        <p className="text-[10px] text-slate-400 leading-normal">
          Generate blocks instantly to verify and confirm multi-sig PSBT broadcasts.
        </p>

        <button
          onClick={handleMineBlock}
          disabled={isMining}
          className="w-full py-2 px-3 rounded-xl neon-btn-primary text-xs font-extrabold flex items-center justify-center gap-2 transition"
        >
          {isMining ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#030712]" />
              Mining Block...
            </>
          ) : (
            <>
              <Pickaxe className="w-3.5 h-3.5 text-[#030712]" />
              Mine 1 Regtest Block
            </>
          )}
        </button>

        {minedSuccess && (
          <div className="flex items-center gap-1.5 text-[10px] text-[#00FF9D] font-mono font-bold drop-shadow-[0_0_8px_rgba(0,255,157,0.6)]">
            <CheckCircle className="w-3.5 h-3.5 text-[#00FF9D]" />
            {minedSuccess}
          </div>
        )}
      </div>
    </aside>
  );
}
