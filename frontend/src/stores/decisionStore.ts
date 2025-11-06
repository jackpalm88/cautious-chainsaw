import { create } from 'zustand';
import { api, DecisionRecordResponse } from '../lib/api';

export interface AgentInsight {
  agent: string;
  statement: string;
}

export interface DecisionRecord {
  id: string;
  timestamp: number;
  action: 'BUY' | 'SELL' | 'HOLD';
  symbol: string;
  confidence: number;
  summary: string;
  rationale: string;
  agentInsights: AgentInsight[];
  riskScore: number;
}

type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

interface DecisionStore {
  recentDecisions: DecisionRecord[];
  selectedDecision: DecisionRecord | null;
  status: AsyncStatus;
  error: string | null;
  hydrate: () => Promise<void>;
  selectDecision: (id: string) => void;
  ingestDecision: (decision: DecisionRecord | DecisionRecordResponse) => void;
}

const mapDecision = (decision: DecisionRecord | DecisionRecordResponse): DecisionRecord => ({
  id: decision.id,
  timestamp: decision.timestamp,
  action: decision.action,
  symbol: decision.symbol,
  confidence: decision.confidence,
  summary: decision.summary,
  rationale: decision.rationale,
  agentInsights: decision.agentInsights,
  riskScore: decision.riskScore
});

const withMessage = (error: unknown): string => {
  if (error instanceof Error) return error.message;
  return 'Unable to load decisions';
};

export const useDecisionStore = create<DecisionStore>((set, get) => ({
  recentDecisions: [],
  selectedDecision: null,
  status: 'idle',
  error: null,
  hydrate: async () => {
    if (get().status === 'loading' || get().status === 'success') return;
    set({ status: 'loading', error: null });
    try {
      const decisions = await api.listDecisions();
      const mapped = decisions.map(mapDecision);
      set({
        recentDecisions: mapped,
        status: 'success',
        selectedDecision: mapped[0] ?? null
      });
    } catch (error) {
      set({ status: 'error', error: withMessage(error) });
    }
  },
  selectDecision: (id: string) => {
    const decision = get().recentDecisions.find((item) => item.id === id) ?? null;
    set({ selectedDecision: decision });
  },
  ingestDecision: (decision: DecisionRecord | DecisionRecordResponse) => {
    const mapped = mapDecision(decision);
    set((state) => ({
      recentDecisions: [mapped, ...state.recentDecisions].slice(0, 50),
      selectedDecision: mapped,
      status: 'success'
    }));
  }
}));
