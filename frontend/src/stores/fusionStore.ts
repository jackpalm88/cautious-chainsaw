import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';

export type SyncStatus = 'disconnected' | 'synced' | 'delayed' | 'stale';

const isMockStreamEnabled = import.meta.env.VITE_USE_MOCK_STREAM === 'true';

export interface OHLCV {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: number;
}

export interface SentimentData {
  score: number;
  articleCount: number;
  latestHeadline: string;
  timestamp: number;
}

export interface EconomicEvent {
  id: string;
  name: string;
  impact: 'low' | 'medium' | 'high';
  actual?: string;
  forecast?: string;
  timestamp: number;
}

interface FusionStore {
  socket: Socket | null;
  symbol: string;
  priceBuffer: OHLCV[];
  sentimentBuffer: SentimentData[];
  eventBuffer: EconomicEvent[];
  connectionStatus: SyncStatus;
  latencyMs: number | null;
  mode: 'live' | 'mock';
  mockIntervalId: number | null;
  connect: (symbol: string) => void;
  disconnect: () => void;
  startMockStream: (symbol: string) => void;
}

const MAX_PRICE_POINTS = 1000;
const MAX_SENTIMENT_POINTS = 500;
const MAX_EVENT_POINTS = 100;

const MOCK_EVENT_CYCLE = [
  {
    name: 'ECB Rate Statement',
    impact: 'high' as const,
    actual: '4.50%',
    forecast: '4.50%'
  },
  {
    name: 'US Non-Farm Payrolls',
    impact: 'high' as const,
    actual: '+195K',
    forecast: '+180K'
  },
  {
    name: 'ISM Manufacturing PMI',
    impact: 'medium' as const,
    actual: '52.4',
    forecast: '51.8'
  },
  {
    name: 'Eurozone CPI Flash',
    impact: 'high' as const,
    actual: '2.7%',
    forecast: '2.5%'
  }
];

const createMockPayloadGenerator = (symbol: string) => {
  let price = 1.085;
  let eventIndex = 0;
  let lastEventAt = 0;
  const headlines = [
    `${symbol} rebounds as traders digest latest macro data`,
    `Analysts eye ${symbol} breakout on improved sentiment`,
    `${symbol} consolidates ahead of major risk event`,
    `${symbol} drifts lower amid mixed economic releases`
  ];
  return () => {
    const now = Date.now();
    const drift = Math.sin(now / 60000) * 0.00025;
    const noise = (Math.random() - 0.5) * 0.0006;
    price = Math.max(1.04, Math.min(1.12, price + drift + noise));
    const close = Number(price.toFixed(5));
    const spread = Math.random() * 0.0004 + 0.0001;
    const high = Number((close + spread).toFixed(5));
    const low = Number((close - spread).toFixed(5));
    const open = Number((close - noise).toFixed(5));
    const sentimentBase = Math.sin(now / 45000);
    const sentimentNoise = (Math.random() - 0.5) * 0.2;
    const sentimentScore = Math.max(-1, Math.min(1, sentimentBase + sentimentNoise));
    let events: EconomicEvent[] = [];
    if (now - lastEventAt > 20000) {
      const template = MOCK_EVENT_CYCLE[eventIndex % MOCK_EVENT_CYCLE.length];
      events = [
        {
          id: `${template.name}-${now}`,
          name: template.name,
          impact: template.impact,
          actual: template.actual,
          forecast: template.forecast,
          timestamp: now / 1000
        }
      ];
      eventIndex += 1;
      lastEventAt = now;
    }

    return {
      timestamp: now / 1000,
      price: {
        open,
        high,
        low,
        close,
        volume: Math.floor(1500 + Math.random() * 2500)
      },
      sentiment: {
        score: sentimentScore,
        article_count: 12 + Math.floor(Math.random() * 12),
        latest_headline: headlines[eventIndex % headlines.length]
      },
      events
    };
  };
};

export const useFusionStore = create<FusionStore>((set, get) => ({
  socket: null,
  symbol: 'EURUSD',
  priceBuffer: [],
  sentimentBuffer: [],
  eventBuffer: [],
  connectionStatus: 'disconnected',
  latencyMs: null,
  mode: isMockStreamEnabled ? 'mock' : 'live',
  mockIntervalId: null,
  connect: (symbol: string) => {
    const existing = get().socket;
    if (existing) {
      existing.disconnect();
    }

    if (isMockStreamEnabled) {
      get().startMockStream(symbol);
      return;
    }

    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    socket.on('connect', () => {
      set({ connectionStatus: 'synced', symbol, mode: 'live' });
      socket.emit('subscribe_fusion', { symbol });
    });

    socket.on('fusion_update', (payload: any) => {
      const now = Date.now();
      const timestamp = (payload.timestamp ?? now) * 1000;
      const latency = now - timestamp;

      set((state) => ({
        latencyMs: latency,
        priceBuffer: [
          ...state.priceBuffer,
          {
            open: payload.price.open,
            high: payload.price.high,
            low: payload.price.low,
            close: payload.price.close,
            volume: payload.price.volume,
            timestamp
          }
        ].slice(-MAX_PRICE_POINTS),
        sentimentBuffer: [
          ...state.sentimentBuffer,
          {
            score: payload.sentiment.score,
            articleCount: payload.sentiment.article_count ?? payload.sentiment.articleCount ?? 0,
            latestHeadline: payload.sentiment.latest_headline ?? payload.sentiment.latestHeadline ?? '—',
            timestamp
          }
        ].slice(-MAX_SENTIMENT_POINTS),
        eventBuffer: payload.events
          ? [
              ...state.eventBuffer,
              ...payload.events.map((event: any) => ({
                id: event.id ?? `${event.name}-${event.timestamp ?? timestamp}`,
                name: event.name,
                impact: event.impact ?? 'medium',
                actual: event.actual,
                forecast: event.forecast,
                timestamp: (event.timestamp ?? timestamp) * 1000
              }))
            ].slice(-MAX_EVENT_POINTS)
          : state.eventBuffer
      }));

      set((state) => ({
        connectionStatus:
          latency <= 100
            ? 'synced'
            : latency <= 500
            ? 'delayed'
            : 'stale'
      }));
    });

    socket.on('disconnect', () => {
      set({ connectionStatus: 'disconnected' });
    });

    set({ socket });
  },
  startMockStream: (symbol: string) => {
    const { mockIntervalId } = get();
    if (mockIntervalId !== null) {
      window.clearInterval(mockIntervalId);
    }

    const generatePayload = createMockPayloadGenerator(symbol);
    let latency = Math.round(35 + Math.random() * 40);
    set({
      symbol,
      connectionStatus: 'synced',
      mode: 'mock',
      latencyMs: latency
    });

    const intervalId = window.setInterval(() => {
      const payload = generatePayload();
      const timestamp = payload.timestamp * 1000;
      latency = Math.round(35 + Math.random() * 40);
      set((state) => ({
        latencyMs: latency,
        priceBuffer: [
          ...state.priceBuffer,
          {
            open: payload.price.open,
            high: payload.price.high,
            low: payload.price.low,
            close: payload.price.close,
            volume: payload.price.volume,
            timestamp
          }
        ].slice(-MAX_PRICE_POINTS),
        sentimentBuffer: [
          ...state.sentimentBuffer,
          {
            score: payload.sentiment.score,
            articleCount: payload.sentiment.article_count,
            latestHeadline: payload.sentiment.latest_headline,
            timestamp
          }
        ].slice(-MAX_SENTIMENT_POINTS),
        eventBuffer:
          payload.events.length > 0
            ? [
                ...state.eventBuffer,
                ...payload.events.map((event) => ({
                  id: event.id,
                  name: event.name,
                  impact: event.impact,
                  actual: event.actual,
                  forecast: event.forecast,
                  timestamp: event.timestamp * 1000
                }))
              ].slice(-MAX_EVENT_POINTS)
            : state.eventBuffer
      }));
    }, 800);

    set({ mockIntervalId: intervalId });
  },
  disconnect: () => {
    const socket = get().socket;
    if (socket) {
      socket.disconnect();
    }
    const { mockIntervalId } = get();
    if (mockIntervalId !== null) {
      window.clearInterval(mockIntervalId);
    }
    set({
      socket: null,
      connectionStatus: 'disconnected',
      latencyMs: null,
      mockIntervalId: null,
      mode: isMockStreamEnabled ? 'mock' : 'live'
    });
  }
}));
