'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, DemoUser, MemberRole } from '@/lib/types';
import { api } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  demoUsers: DemoUser[];
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  quickLogin: (user: DemoUser) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  hasRole: (roles: MemberRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [demoUsers, setDemoUsers] = useState<DemoUser[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchDemoUsers = async () => {
    try {
      const demos = await api.getDemoUsers();
      setDemoUsers(demos);
    } catch (e) {
      console.warn('Could not load demo users:', e);
    }
  };

  const refreshUser = async () => {
    try {
      const me = await api.getMe();
      setUser(me);
      if (typeof window !== 'undefined') {
        localStorage.setItem('sg_user', JSON.stringify(me));
      }
    } catch {
      setUser(null);
      api.clearToken();
    }
  };

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await fetchDemoUsers();
      const savedUser = typeof window !== 'undefined' ? localStorage.getItem('sg_user') : null;
      if (savedUser) {
        try {
          setUser(JSON.parse(savedUser));
          await refreshUser();
        } catch {
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    init();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.login(email, password);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const quickLogin = async (demoUser: DemoUser) => {
    setIsLoading(true);
    try {
      // Demo password is "password123" for all seeded profiles
      const res = await api.login(demoUser.email, 'password123');
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.clearToken();
    setUser(null);
  };

  const hasRole = (roles: MemberRole[]): boolean => {
    if (!user || !user.role) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        demoUsers,
        isLoading,
        login,
        quickLogin,
        logout,
        refreshUser,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
