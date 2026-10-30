'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from './RoleContext';
import { api } from '@/lib/api';
import { NodeInfo, NotificationItem } from '@/lib/types';
import {
  Shield, Bell, CheckCircle2, AlertTriangle, Info,
  ChevronDown, UserCheck, RefreshCw, LogOut, Cpu, Zap
} from 'lucide-react';

export default function Navbar() {
  const { user, demoUsers, quickLogin, logout } = useAuth();
  const [nodeInfo, setNodeInfo] = useState<NodeInfo | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const info = await api.getNodeInfo();
        setNodeInfo(info);
      } catch (e) {
        console.warn('Node info error:', e);
      }
      if (user) {
        try {
          const notifs = await api.getNotifications();
          setNotifications(notifs);
        } catch {}
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 8000);
    return () => clearInterval(interval);
  }, [user]);

  const unreadCount = notifications.filter(n => !n.read_status).length;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#00F0FF]/20 bg-[#030712]/90 backdrop-blur-xl shadow-[0_4px_30px_rgba(0,0,0,0.8)]">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00F0FF] via-blue-600 to-[#A855F7] p-[1.5px] shadow-[0_0_20px_rgba(0,240,255,0.4)] group-hover:shadow-[0_0_30px_rgba(0,240,255,0.7)] transition-all">
              <div className="w-full h-full bg-[#030712] rounded-[10px] flex items-center justify-center">
                <Shield className="w-5 h-5 text-[#00F0FF] drop-shadow-[0_0_8px_rgba(0,240,255,0.8)]" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight text-white">
                  Satoshi<span className="text-[#00F0FF] drop-shadow-[0_0_12px_rgba(0,240,255,0.6)]">Guard</span>
                </span>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full neon-badge-cyan">
                  NEON VAULT
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono tracking-wider">BITCOIN MULTISIG PROTOCOL</p>
            </div>
          </Link>
        </div>

        {/* Center: Live Bitcoin Node Badge with Neon Glow */}
        <div className="hidden md:flex items-center gap-3 px-3.5 py-1.5 rounded-full bg-[#070D1E] border border-[#00F0FF]/30 shadow-[0_0_15px_-3px_rgba(0,240,255,0.25)] text-xs">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00FF9D] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#00FF9D] shadow-[0_0_8px_#00FF9D]"></span>
          </span>
          <Cpu className="w-3.5 h-3.5 text-[#00F0FF]" />
          <span className="font-semibold text-slate-200 tracking-wide text-[11px]">
            Bitcoin Regtest
          </span>
          <span className="text-slate-600">•</span>
          <span className="font-mono text-[#00F0FF] font-bold text-[11px] drop-shadow-[0_0_6px_rgba(0,240,255,0.5)]">
            Block #{nodeInfo ? nodeInfo.blocks : '---'}
          </span>
        </div>

        {/* Right: Notifications & Persona Switcher */}
        <div className="flex items-center gap-3">
          {/* Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowNotifMenu(!showNotifMenu)}
              className="relative p-2 rounded-xl bg-[#070D1E] border border-slate-800 hover:border-[#00F0FF]/40 text-slate-300 hover:text-[#00F0FF] hover:shadow-[0_0_15px_rgba(0,240,255,0.2)] transition"
              title="Audit Alerts"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-[#FF1E56] text-[10px] font-extrabold text-white shadow-[0_0_10px_#FF1E56]">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifMenu && (
              <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-[#070D1E]/95 border border-[#00F0FF]/30 shadow-[0_15px_50px_rgba(0,0,0,0.9)] p-3 z-50 backdrop-blur-2xl">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                  <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-[#00F0FF]" />
                    Audit & Alerts
                  </span>
                  {unreadCount > 0 && (
                    <button
                      onClick={async () => {
                        await api.markAllNotificationsRead();
                        setNotifications(prev => prev.map(n => ({ ...n, read_status: true })));
                      }}
                      className="text-[11px] text-[#00F0FF] hover:underline"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                <div className="max-h-72 overflow-y-auto space-y-2">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500">No new alerts</div>
                  ) : (
                    notifications.map(n => (
                      <div
                        key={n.id}
                        className={`p-2.5 rounded-xl border text-xs transition ${
                          n.read_status
                            ? 'bg-[#030712]/50 border-slate-800 text-slate-400'
                            : 'bg-[#00F0FF]/5 border-[#00F0FF]/30 text-slate-200 shadow-[0_0_12px_-4px_rgba(0,240,255,0.2)]'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          {n.category === 'WARNING' ? (
                            <AlertTriangle className="w-4 h-4 text-[#FFB800] shrink-0 mt-0.5 drop-shadow-[0_0_6px_#FFB800]" />
                          ) : n.category === 'SUCCESS' ? (
                            <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0 mt-0.5 drop-shadow-[0_0_6px_#00FF9D]" />
                          ) : (
                            <Info className="w-4 h-4 text-[#00F0FF] shrink-0 mt-0.5 drop-shadow-[0_0_6px_#00F0FF]" />
                          )}
                          <div>
                            <div className="font-bold text-white">{n.title}</div>
                            <div className="text-[11px] text-slate-300 mt-0.5">{n.message}</div>
                            <div className="text-[10px] text-slate-500 mt-1 font-mono">
                              {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User & 1-Click Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#070D1E] border border-slate-800 hover:border-[#00F0FF]/40 hover:shadow-[0_0_15px_rgba(0,240,255,0.25)] transition"
            >
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#00F0FF] to-[#A855F7] flex items-center justify-center text-xs font-black text-[#030712] shadow-[0_0_10px_rgba(0,240,255,0.5)]">
                {user ? user.full_name.charAt(0) : 'U'}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-xs font-bold text-white leading-tight">
                  {user ? user.full_name.split(' ')[0] : 'Demo User'}
                </div>
                <div className="text-[10px] font-mono text-[#00F0FF] leading-tight font-semibold">
                  {user?.role || 'SIGNER'}
                </div>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {showRoleMenu && (
              <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-[#070D1E]/95 border border-[#00F0FF]/30 shadow-[0_15px_50px_rgba(0,0,0,0.9)] p-2 z-50 backdrop-blur-2xl">
                <div className="px-3 py-2 border-b border-slate-800 mb-1">
                  <div className="text-xs font-bold text-white">{user?.full_name}</div>
                  <div className="text-[11px] text-slate-400 truncate font-mono">{user?.email}</div>
                  <div className="mt-1.5 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold neon-badge-cyan uppercase">
                    Role: {user?.role}
                  </div>
                </div>

                <div className="px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-[#00F0FF] flex items-center gap-1">
                  <Zap className="w-3 h-3 text-[#00F0FF]" />
                  Switch Demo Persona (1-Click)
                </div>

                <div className="space-y-1">
                  {demoUsers.map(du => (
                    <button
                      key={du.id}
                      onClick={async () => {
                        await quickLogin(du);
                        setShowRoleMenu(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between transition ${
                        user?.email === du.email
                          ? 'bg-[#00F0FF]/15 text-[#00F0FF] font-bold border border-[#00F0FF]/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                          : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                      }`}
                    >
                      <div>
                        <div className="font-semibold">{du.full_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{du.role}</div>
                      </div>
                      {du.has_signer_key && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold neon-badge-emerald">
                          Signer
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                <div className="mt-2 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => {
                      logout();
                      setShowRoleMenu(false);
                    }}
                    className="w-full px-3 py-1.5 rounded-xl text-xs text-[#FF1E56] hover:bg-[#FF1E56]/10 flex items-center gap-2 transition font-semibold"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
