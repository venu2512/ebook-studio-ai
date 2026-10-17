"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { User } from "@ebook/shared";

import { authApi } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/client";
import { queryKeys } from "@/lib/query/keys";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<User>;
  loginWithGoogle: (idToken?: string, code?: string) => Promise<User>;
  register: (email: string, password: string, fullName?: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: queryKeys.me,
    queryFn: () => authApi.me(),
    enabled: typeof window !== "undefined" && tokenStore.access() !== null,
    retry: false,
    staleTime: 60_000,
  });

  const user = data ?? null;

  const login = React.useCallback(
    async (email: string, password: string) => {
      await authApi.login({ email, password });
      const me = await authApi.me();
      queryClient.setQueryData(queryKeys.me, me);
      return me;
    },
    [queryClient],
  );

  const loginWithGoogle = React.useCallback(
    async (idToken?: string, code?: string) => {
      await authApi.google({ id_token: idToken, code });
      const me = await authApi.me();
      queryClient.setQueryData(queryKeys.me, me);
      return me;
    },
    [queryClient],
  );


  const register = React.useCallback(
    async (email: string, password: string, fullName?: string) => {
      await authApi.register({ email, password, full_name: fullName || null });
      // The register endpoint does not expose the access token to the browser,
      // so we sign in right after to obtain one.
      await authApi.login({ email, password });
      const me = await authApi.me();
      queryClient.setQueryData(queryKeys.me, me);
      return me;
    },
    [queryClient],
  );

  const logout = React.useCallback(async () => {
    await authApi.logout();
    queryClient.setQueryData(queryKeys.me, null);
    queryClient.clear();
  }, [queryClient]);

  const refresh = React.useCallback(async () => {
    await refetch();
  }, [refetch]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === "admin",
      login,
      loginWithGoogle,
      register,
      logout,
      refresh,
    }),
    [user, isLoading, login, loginWithGoogle, register, logout, refresh],
  );


  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
