import { create } from 'zustand';

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

interface DecisionStore {
  recentDecisions: DecisionRecord[];
  selectedDecision: DecisionRecord | null;
  selectDecision: (id: string) => void;
  ingestDecision: (decision: DecisionRecord) => void;
}

const FAKE_DECISIONS: DecisionRecord[] = [
  {
    id: 'dec-001',
    timestamp: Date.now() - 60_000,
    action: 'BUY',
    symbol: 'EURUSD',
    confidence: 0.72,
    summary: 'Momentum alignment across price and sentiment streams.',
    rationale: 'Price action forms higher high with positive sentiment delta and no conflicting macro events.',
    agentInsights: [
      { agent: 'Market Intelligence', statement: 'News sentiment shifted +0.32 in the last 3 minutes.' },
      { agent: 'Low-Level Reflection', statement: 'Latency within 75ms; price momentum intact.' },
      { agent: 'High-Level Reflection', statement: 'No conflicting positions; risk-on regime persists.' },
      { agent: 'Decision Agent', statement: 'Enter with 1.5% risk, stop below liquidity pocket at 1.0832.' }
    ],
    riskScore: 0.38
  },
  {
    id: 'dec-002',
    timestamp: Date.now() - 300_000,
    action: 'HOLD',
    symbol: 'GBPUSD',
    confidence: 0.54,
    summary: 'Conflicting macro sentiment – waiting for clarification.',
    rationale: 'Economic surprise index in UK remains negative; prefer to observe upcoming GDP release.',
    agentInsights: [
      { agent: 'Market Intelligence', statement: 'Social sentiment is neutral, article velocity decreasing.' },
      { agent: 'Low-Level Reflection', statement: 'Price volatility expanding, but no break in structure yet.' },
      { agent: 'High-Level Reflection', statement: 'Macro regime uncertain; risk budget nearly exhausted.' },
      { agent: 'Decision Agent', statement: 'Maintain current exposure; revisit after GDP print.' }
    ],
    riskScore: 0.61
  }
];

export const useDecisionStore = create<DecisionStore>((set, get) => ({
  recentDecisions: FAKE_DECISIONS,
  selectedDecision: null,
  selectDecision: (id: string) => {
    const decision = get().recentDecisions.find((d) => d.id === id) ?? null;
    set({ selectedDecision: decision });
  },
  ingestDecision: (decision: DecisionRecord) => {
    set((state) => ({
      recentDecisions: [decision, ...state.recentDecisions].slice(0, 20),
      selectedDecision: decision
    }));
  }
}));
