'use client';

import React, { useState, useEffect } from 'react';
import AppLayout from '@/components/AppLayout';
import { useAuth } from '@/components/RoleContext';
import { api } from '@/lib/api';
import { NodeInfo } from '@/lib/types';
import {
  Settings, Cpu, Pickaxe, CheckCircle2, RefreshCw,
  Loader2, Shield, User, Building, HardDrive, Terminal
} from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuth();
  const [nodeInfo, setNodeInfo] = useState<NodeInfo | null>(null);
  const [isMining, setIsMining] = useState<boolean>(false);
  const [mineResult, setMineResult] = useState<string | null>(null);
  const [blocksToMine, setBlocksToMine] = useState<number>(1);

  const fetchNodeInfo = async () => {
    try {
      const info = await api.getNodeInfo();
      setNodeInfo(info);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchNodeInfo();
  }, []);

  const handleMine = async () => {
    setIsMining(true);
    setMineResult(null);
    try {
      const res = await api.mineBlocks(blocksToMine);
      setMineResult(`Successfully mined ${res.mined_blocks} block(s)! New block height: #${res.new_height}`);
      await fetchNodeInfo();
    } catch (err: any) {
      alert(err.message || 'Mining failed');
    } finally {
      setIsMining(false);
    }
  };

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyan-900/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">System Configuration & Node Controls</h1>
            <span className="neon-badge-cyan text-[10px] font-mono px-2 py-0.5 rounded-full uppercase tracking-wider font-semibold">
              Regtest RPC
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Bitcoin Core Regtest RPC parameters, organization profile, and development blockchain utilities
          </p>
        </div>

        <button
          onClick={fetchNodeInfo}
          className="px-4 py-2 rounded-xl bg-slate-900/90 border border-cyan-900/60 text-xs text-cyan-300 hover:text-white hover:border-cyan-400 flex items-center gap-2 transition hover:shadow-[0_0_15px_rgba(0,240,255,0.2)] font-mono font-bold"
        >
          <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
          Poll Node Status
        </button>
      </div>

      {mineResult && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-xs text-emerald-300 flex items-center gap-2.5 shadow-[0_0_20px_rgba(0,255,157,0.15)]">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="font-medium">{mineResult}</span>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Bitcoin Core Regtest RPC Diagnostic */}
        <div className="p-6 rounded-2xl neon-card space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-cyan-950">
            <span className="p-2 rounded-xl bg-cyan-950/60 text-cyan-400 border border-cyan-500/30">
              <Cpu className="w-4 h-4" />
            </span>
            <div>
              <h2 className="text-sm font-extrabold text-white tracking-wide">Bitcoin Core Regtest Node</h2>
              <p className="text-xs text-slate-400">Direct JSON-RPC localhost socket connection</p>
            </div>
          </div>

          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
              <span className="text-slate-400 font-sans">RPC Status:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#00FF9D] animate-pulse" />
                {nodeInfo?.status || 'CONNECTED'}
              </span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
              <span className="text-slate-400 font-sans">Network / Chain:</span>
              <span className="text-cyan-400 uppercase font-bold tracking-wider">{nodeInfo?.chain || 'regtest'}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
              <span className="text-slate-400 font-sans">Block Height:</span>
              <span className="text-white font-extrabold neon-glow-text-cyan">#{nodeInfo?.blocks ?? '---'}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
              <span className="text-slate-400 font-sans">Software Subversion:</span>
              <span className="text-slate-300">{nodeInfo?.subversion || '/Satoshi:28.0.0/'}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-cyan-950/80">
              <span className="text-slate-400 font-sans">RPC Endpoint:</span>
              <span className="text-slate-400">http://127.0.0.1:18443</span>
            </div>

            <div className="flex justify-between py-1.5">
              <span className="text-slate-400 font-sans">Best Block Hash:</span>
              <span className="text-[10px] text-cyan-400/70 truncate max-w-xs select-all">
                {nodeInfo?.bestblockhash || '0f9188f1...'}
              </span>
            </div>
          </div>
        </div>

        {/* Interactive Regtest Block Generator */}
        <div className="p-6 rounded-2xl neon-card-emerald space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3 pb-3 border-b border-emerald-950/80">
              <span className="p-2 rounded-xl bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                <Pickaxe className="w-4 h-4" />
              </span>
              <div>
                <h2 className="text-sm font-extrabold text-white tracking-wide">Regtest Mining Console</h2>
                <p className="text-xs text-slate-400">Advance local blockchain blocks on demand</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              In Bitcoin Regtest mode, blocks are produced deterministically on demand. Use this console to mine new blocks and confirm any broadcast multisig transactions instantly.
            </p>

            <div className="flex items-center gap-3 pt-2">
              <label className="text-xs text-slate-400 font-semibold font-sans">Blocks to mine:</label>
              {[1, 5, 10].map(cnt => (
                <button
                  key={cnt}
                  type="button"
                  onClick={() => setBlocksToMine(cnt)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition ${
                    blocksToMine === cnt
                      ? 'neon-badge-emerald font-extrabold shadow-[0_0_12px_rgba(0,255,157,0.3)]'
                      : 'bg-slate-950/80 text-slate-400 hover:text-white border border-emerald-900/30'
                  }`}
                >
                  +{cnt} Block{cnt > 1 ? 's' : ''}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleMine}
            disabled={isMining}
            className="w-full py-2.5 px-4 rounded-xl neon-btn-emerald disabled:opacity-50 text-xs font-extrabold flex items-center justify-center gap-2 transition"
          >
            {isMining ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Mining {blocksToMine} block(s)...
              </>
            ) : (
              <>
                <Pickaxe className="w-3.5 h-3.5" />
                Trigger Mining of {blocksToMine} Block{blocksToMine > 1 ? 's' : ''}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Organization & Profile Details */}
      <div className="p-6 rounded-2xl neon-card space-y-4">
        <div className="flex items-center gap-2 pb-2 border-b border-cyan-950">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-extrabold text-white tracking-wide">Organization & Operator Identity</h2>
        </div>

        <div className="grid md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-900/40 space-y-1">
            <span className="text-slate-500 font-sans font-medium text-[11px]">Enterprise Name</span>
            <div className="font-bold text-white text-sm font-sans">BitFortress Capital & Treasury</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-900/40 space-y-1">
            <span className="text-slate-500 font-sans font-medium text-[11px]">Active Custodian</span>
            <div className="font-bold text-white text-sm font-sans">{user?.full_name || 'Sarah Lin'}</div>
            <div className="text-[10px] text-cyan-400/80">{user?.email || 'admin@bitfortress.io'}</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-cyan-900/40 space-y-1">
            <span className="text-slate-500 font-sans font-medium text-[11px]">Assigned Role</span>
            <div className="font-bold text-cyan-300 text-sm">{user?.role || 'ORG_ADMIN'}</div>
            <div className="text-[10px] text-slate-500 font-sans">Strictly enforced by FastAPI backend</div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
