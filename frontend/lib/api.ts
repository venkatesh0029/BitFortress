import {
  User, DemoUser, TreasuryWallet, TransactionProposal, SpendingPolicy,
  AuditEvent, NotificationItem, NodeInfo
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('sg_token');
  }

  public setToken(token: string) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('sg_token', token);
    }
  }

  public clearToken() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('sg_token');
      localStorage.removeItem('sg_user');
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorDetail = 'API Request Failed';
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorJson.message || errorDetail;
      } catch {
        errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      }
      throw new Error(errorDetail);
    }

    return response.json() as Promise<T>;
  }

  // Auth
  async login(email: string, password: string) {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(res.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('sg_user', JSON.stringify(res.user));
    }
    return res;
  }

  async register(email: string, full_name: string, password: string, org_name?: string) {
    const url = org_name ? `/auth/register?org_name=${encodeURIComponent(org_name)}` : '/auth/register';
    const res = await this.request<{ access_token: string; user: User }>(url, {
      method: 'POST',
      body: JSON.stringify({ email, full_name, password }),
    });
    this.setToken(res.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('sg_user', JSON.stringify(res.user));
    }
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async getDemoUsers(): Promise<DemoUser[]> {
    return this.request<DemoUser[]>('/auth/demo-users');
  }

  // Treasury
  async getTreasuries(): Promise<TreasuryWallet[]> {
    return this.request<TreasuryWallet[]>('/treasury');
  }

  async getTreasury(id: number): Promise<TreasuryWallet> {
    return this.request<TreasuryWallet>(`/treasury/${id}`);
  }

  async createTreasury(wallet_name: string, threshold: number, signer_ids: number[]): Promise<TreasuryWallet> {
    return this.request<TreasuryWallet>('/treasury', {
      method: 'POST',
      body: JSON.stringify({ wallet_name, threshold, signer_ids }),
    });
  }

  async fundTreasury(wallet_id: number, amount_btc: number = 5.0) {
    return this.request<any>(`/treasury/${wallet_id}/fund`, {
      method: 'POST',
      body: JSON.stringify({ wallet_id, amount_btc }),
    });
  }

  async syncTreasury(wallet_id: number) {
    return this.request<{ wallet_id: number; balance_satoshis: number; balance_btc: number }>(`/treasury/${wallet_id}/sync`, {
      method: 'POST',
    });
  }

  // Transactions
  async getTransactions(wallet_id?: number, status?: string): Promise<TransactionProposal[]> {
    let url = '/transactions';
    const params = new URLSearchParams();
    if (wallet_id) params.append('wallet_id', wallet_id.toString());
    if (status) params.append('status', status);
    if (params.toString()) url += `?${params.toString()}`;
    return this.request<TransactionProposal[]>(url);
  }

  async getTransaction(id: number): Promise<TransactionProposal> {
    return this.request<TransactionProposal>(`/transactions/${id}`);
  }

  async proposeTransaction(wallet_id: number, destination: string, amount_satoshis: number, fee_satoshis: number, description: string): Promise<TransactionProposal> {
    return this.request<TransactionProposal>('/transactions', {
      method: 'POST',
      body: JSON.stringify({
        wallet_id,
        destination,
        amount_satoshis,
        fee_satoshis,
        description,
      }),
    });
  }

  // Approvals
  async getPendingApprovals(): Promise<TransactionProposal[]> {
    return this.request<TransactionProposal[]>('/approvals/pending');
  }

  async signProposal(proposal_id: number, signed_psbt?: string, signature_hex?: string, signature_reference?: string) {
    return this.request<any>('/approvals/sign', {
      method: 'POST',
      body: JSON.stringify({
        proposal_id,
        signed_psbt,
        signature_hex,
        signature_reference,
      }),
    });
  }

  async rejectProposal(proposal_id: number, reason: string) {
    return this.request<any>('/approvals/reject', {
      method: 'POST',
      body: JSON.stringify({ proposal_id, reason }),
    });
  }

  // Signers
  async getSigners() {
    return this.request<any[]>('/signers');
  }

  async registerSigner(label: string, public_key: string, fingerprint?: string, derivation_path?: string) {
    return this.request<any>('/signers', {
      method: 'POST',
      body: JSON.stringify({ label, public_key, fingerprint, derivation_path }),
    });
  }

  async generateKeypair() {
    return this.request<{ private_key: string; public_key: string; fingerprint: string; derivation_path: string }>('/signers/generate-keypair', {
      method: 'POST',
    });
  }

  async deviceSignPSBT(signer_id: number, psbt_base64: string): Promise<{ signed_psbt: string; complete: boolean; signer_id: number }> {
    return this.request<{ signed_psbt: string; complete: boolean; signer_id: number }>(`/signers/${signer_id}/device-sign`, {
      method: 'POST',
      body: JSON.stringify({ psbt_base64 }),
    });
  }

  // Policies
  async getPolicy(): Promise<SpendingPolicy> {
    return this.request<SpendingPolicy>('/policies');
  }

  async updatePolicy(per_transaction_limit: number, daily_limit: number, require_admin_override: boolean = true): Promise<SpendingPolicy> {
    return this.request<SpendingPolicy>('/policies', {
      method: 'PUT',
      body: JSON.stringify({ per_transaction_limit, daily_limit, require_admin_override }),
    });
  }

  // Audit
  async getAuditTrail(eventType?: string, limit: number = 100): Promise<AuditEvent[]> {
    let url = `/audit?limit=${limit}`;
    if (eventType) url += `&event_type=${encodeURIComponent(eventType)}`;
    return this.request<AuditEvent[]>(url);
  }

  async verifyAuditTrail(): Promise<{ is_valid: boolean; total_records: number; latest_hash: string; message: string; broken_at_id?: number }> {
    return this.request<{ is_valid: boolean; total_records: number; latest_hash: string; message: string; broken_at_id?: number }>('/audit/verify');
  }

  // Notifications
  async getNotifications(): Promise<NotificationItem[]> {
    return this.request<NotificationItem[]>('/notifications');
  }

  async markNotificationRead(id: number) {
    return this.request<any>(`/notifications/${id}/read`, { method: 'POST' });
  }

  async markAllNotificationsRead() {
    return this.request<any>('/notifications/read-all', { method: 'POST' });
  }

  // Node
  async getNodeInfo(): Promise<NodeInfo> {
    return this.request<NodeInfo>('/node/info');
  }

  async mineBlocks(blocks: number = 1) {
    return this.request<any>('/node/mine', {
      method: 'POST',
      body: JSON.stringify({ blocks }),
    });
  }
}

export const api = new ApiClient();
