export type MemberRole = 'ORG_ADMIN' | 'FINANCE_MANAGER' | 'SIGNER' | 'AUDITOR' | 'SYSTEM_OPERATOR';

export type ProposalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'FINALIZED' | 'BROADCAST' | 'CONFIRMED';

export type ApprovalDecision = 'APPROVED' | 'REJECTED';

export interface User {
  id: number;
  email: string;
  full_name: string;
  status: string;
  role?: MemberRole;
  organization_id?: number;
  created_at: string;
}

export interface DemoUser {
  id: number;
  email: string;
  full_name: string;
  role: MemberRole;
  has_signer_key: boolean;
  signer_label: string | null;
  public_key: string | null;
}

export interface TreasurySignerInfo {
  signer_id: number;
  label: string;
  public_key: string;
  user_name: string;
}

export interface TreasuryWallet {
  id: number;
  organization_id: number;
  wallet_name: string;
  address: string;
  threshold: number;
  total_signers: number;
  descriptor?: string;
  redeem_script?: string;
  balance_satoshis: number;
  balance_btc: number;
  network: string;
  status: string;
  created_at: string;
  signers: TreasurySignerInfo[];
}

export interface Approval {
  id: number;
  signer_id: number;
  signer_name: string;
  signer_label: string;
  public_key: string;
  decision: ApprovalDecision;
  signature_reference?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface TransactionProposal {
  id: number;
  wallet_id: number;
  wallet_name: string;
  proposer_id: number;
  proposer_name: string;
  destination: string;
  amount_satoshis: number;
  amount_btc: number;
  fee_satoshis: number;
  description: string;
  status: ProposalStatus;
  txid?: string;
  broadcast_at?: string;
  confirmations: number;
  threshold: number;
  approvals_count: number;
  rejections_count: number;
  created_at: string;
  updated_at: string;
  unsigned_psbt?: string;
  current_psbt?: string;
  finalized_tx_hex?: string;
  approvals?: Approval[];
  signers?: TreasurySignerInfo[];
}

export interface SpendingPolicy {
  id: number;
  organization_id: number;
  per_transaction_limit: number;
  daily_limit: number;
  per_tx_btc: number;
  daily_btc: number;
  require_admin_override: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  organization_id: number;
  actor_id?: number;
  actor_name?: string;
  event_type: string;
  reference_type?: string;
  reference_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  message: string;
  category: string;
  read_status: boolean;
  created_at: string;
}

export interface NodeInfo {
  status: string;
  chain: string;
  blocks: number;
  headers: number;
  bestblockhash: string;
  difficulty: number;
  subversion: string;
  connections: number;
  protocolversion: number;
}
