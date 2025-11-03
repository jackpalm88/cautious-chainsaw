import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';

export type SyncStatus = 'disconnected' | 'synced' | 'delayed' | 'stale';

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
  connect: (symbol: string) => void;
  disconnect: () => void;
}

const MAX_PRICE_POINTS = 1000;
const MAX_SENTIMENT_POINTS = 500;
const MAX_EVENT_POINTS = 100;

export const useFusionStore = create<FusionStore>((set, get) => ({
  socket: null,
  symbol: 'EURUSD',
  priceBuffer: [],
  sentimentBuffer: [],
  eventBuffer: [],
  connectionStatus: 'disconnected',
  latencyMs: null,
  connect: (symbol: string) => {
    const existing = get().socket;
    if (existing) {
      existing.disconnect();
    }

    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    socket.on('connect', () => {
      set({ connectionStatus: 'synced', symbol });
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
  disconnect: () => {
    const socket = get().socket;
    if (socket) {
      socket.disconnect();
    }
    set({ socket: null, connectionStatus: 'disconnected' });
  }
}));
