# 🚀 Trading System UI - Implementation Roadmap

**Projekts:** Financial Trading Agent v2.0 UI Layer  
**Datums:** 2025-11-03  
**Status:** Ready to Start  
**Estimated Duration:** 4-6 weeks (MVP)

---

## 📋 Executive Summary

Šis dokuments sniedz **konkrētu, step-by-step implementation plan** Trading System UI izveidei, balstoties uz INoT Deep Dive stratēģisko analīzi.

**MVP Scope (4 weeks):**
- ✅ Live Trading Dashboard (real-time data fusion viz)
- ✅ Strategy Backtesting Workbench (equity curves + metrics)
- ✅ INoT Decision Explainer (4-agent reasoning trace)
- ✅ Basic Risk Controls (position sizing, emergency stop)

**Tech Stack:**
- Backend: Flask + python-socketio + SQLite
- Frontend: React 18 + Vite + TypeScript + TailwindCSS + Zustand
- Charts: Recharts + D3.js (candlesticks)
- Deployment: Docker + Nginx

---

## 🎯 Sprint Breakdown (4-Week MVP)

### Sprint 1: Foundations (Week 1)
**Goal:** Setup infrastructure, WebSocket communication, basic UI skeleton

**Days 1-2: Backend WebSocket Server**
- Flask app initialization
- python-socketio integration
- Mock data emission (price stream)
- CORS configuration

**Days 3-4: React Project Setup**
- Vite + TypeScript + TailwindCSS initialization
- Zustand store creation
- socket.io-client connection
- Basic routing (React Router)

**Day 5: Live Dashboard Skeleton**
- 3-panel grid layout
- Empty chart containers
- Sync indicator placeholder

**Deliverables:**
- ✅ WebSocket server emitting mock price data
- ✅ React app displaying real-time connection status
- ✅ Basic dashboard layout (no data yet)

---

### Sprint 2: Live Dashboard (Week 2)
**Goal:** Real-time data fusion visualization with 3 streams

**Days 1-2: Price Chart Panel**
- Recharts candlestick implementation
- Volume bar chart
- Zoom/pan functionality
- Time axis formatting

**Day 3: Sentiment Stream Panel**
- Line chart for sentiment score
- Article ticker (last 5 headlines)
- Color-coded sentiment (green/yellow/red)

**Day 4: Economic Events Panel**
- Timeline visualization (D3.js)
- Event impact indicators (H/M/L)
- Tooltip with event details

**Day 5: Temporal Sync Indicator**
- Calculate alignment window (100ms)
- Visual indicator (green/yellow/red)
- Latency metrics display

**Deliverables:**
- ✅ 3 panels displaying live data
- ✅ Sync indicator functional
- ✅ Smooth 100ms updates (no lag)

---

### Sprint 3: Strategy Backtesting (Week 3)
**Goal:** Interactive backtesting workbench with visualizations

**Days 1-2: Backend API Endpoints**
- `/api/strategies` (list all strategies)
- `/api/backtest/:id` (fetch results)
- `/api/backtest/run` (execute backtest)
- SQLite schema for results storage

**Days 3-4: Backtest Workbench UI**
- Strategy selector dropdown
- Date range picker
- Equity curve chart (Recharts)
- Drawdown chart
- Performance metrics table

**Day 5: Trade List & Filters**
- DataGrid component (trade list)
- Filters (winners/losers, long/short)
- Click trade → highlight on chart
- Export to CSV

**Deliverables:**
- ✅ Can run backtest from UI
- ✅ Equity curve + metrics displayed
- ✅ Trade list filterable

---

### Sprint 4: INoT Explainer + Polish (Week 4)
**Goal:** Decision transparency, risk controls, testing

**Days 1-2: INoT Decision Explainer**
- Decision Log Table (bottom of dashboard)
- Decision Detail Modal
- 4-agent debate accordion
- Confidence gauge visualization

**Day 3: Risk Control Center**
- Position sizing calculator
- Emergency stop button
- Risk metrics panel (DD, exposure)

**Days 4-5: Testing & Deployment**
- Playwright E2E tests
- Docker Compose setup
- Nginx configuration
- Production deployment

**Deliverables:**
- ✅ Decision explanations visible
- ✅ Risk controls functional
- ✅ Production-ready deployment

---

## 📁 Project Structure

```
financial-agent/
├── backend/
│   ├── app.py                    # Flask main app
│   ├── websocket_server.py       # SocketIO server
│   ├── api/
│   │   ├── __init__.py
│   │   ├── strategy_routes.py    # Strategy endpoints
│   │   ├── backtest_routes.py    # Backtest endpoints
│   │   └── decision_routes.py    # INoT decision endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── strategy.py           # Strategy ORM
│   │   └── decision.py           # Decision ORM
│   └── requirements.txt          # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx              # React entry point
│   │   ├── App.tsx               # Root component
│   │   ├── pages/
│   │   │   ├── LiveDashboard.tsx
│   │   │   ├── BacktestWorkbench.tsx
│   │   │   └── SystemMonitor.tsx
│   │   ├── components/
│   │   │   ├── LiveDashboard/
│   │   │   │   ├── PriceChartPanel.tsx
│   │   │   │   ├── SentimentPanel.tsx
│   │   │   │   ├── EconomicEventsPanel.tsx
│   │   │   │   └── SyncIndicator.tsx
│   │   │   ├── Backtesting/
│   │   │   │   ├── StrategySelector.tsx
│   │   │   │   ├── EquityCurveChart.tsx
│   │   │   │   ├── MetricsTable.tsx
│   │   │   │   └── TradeListGrid.tsx
│   │   │   ├── INoT/
│   │   │   │   ├── DecisionLogTable.tsx
│   │   │   │   ├── DecisionDetailModal.tsx
│   │   │   │   └── ConfidenceGauge.tsx
│   │   │   └── RiskControl/
│   │   │       ├── PositionSizingCalculator.tsx
│   │   │       └── EmergencyStopButton.tsx
│   │   ├── stores/
│   │   │   ├── fusionStore.ts    # Real-time data state
│   │   │   ├── backtestStore.ts  # Backtest state
│   │   │   └── decisionStore.ts  # INoT decisions state
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts   # WebSocket connection hook
│   │   │   └── useBacktest.ts    # Backtest API hook
│   │   └── utils/
│   │       ├── formatters.ts     # Number/date formatting
│   │       └── chartHelpers.ts   # Chart utilities
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
├── tests/
│   ├── e2e/
│   │   ├── live-dashboard.spec.ts
│   │   ├── backtest-workflow.spec.ts
│   │   └── decision-explainer.spec.ts
│   └── integration/
│       ├── test_websocket.py
│       └── test_backtest_api.py
│
└── docs/
    ├── UI_ARCHITECTURE_INOT_ANALYSIS.md
    └── IMPLEMENTATION_ROADMAP.md (šis dokuments)
```

---

## 🔧 Detailed Implementation Guide

### Part 1: Backend WebSocket Server

#### Step 1.1: Flask App Initialization

```python
# backend/app.py
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Import routes
from api import strategy_routes, backtest_routes, decision_routes

app.register_blueprint(strategy_routes.bp, url_prefix='/api')
app.register_blueprint(backtest_routes.bp, url_prefix='/api')
app.register_blueprint(decision_routes.bp, url_prefix='/api')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
```

#### Step 1.2: WebSocket Server Implementation

```python
# backend/websocket_server.py
from flask_socketio import emit
from datetime import datetime
import random
from threading import Thread
import time

class WebSocketServer:
    def __init__(self, socketio, fusion_engine):
        self.socketio = socketio
        self.fusion_engine = fusion_engine
        self.active_subscriptions = {}  # {session_id: symbol}
        
    def start(self):
        """Start WebSocket server with event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            print(f'Client connected: {request.sid}')
            emit('connection_status', {'status': 'connected'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(f'Client disconnected: {request.sid}')
            if request.sid in self.active_subscriptions:
                del self.active_subscriptions[request.sid]
        
        @self.socketio.on('subscribe_fusion')
        def handle_subscribe(data):
            symbol = data.get('symbol', 'EURUSD')
            self.active_subscriptions[request.sid] = symbol
            
            # Start emitting data for this session
            thread = Thread(target=self._emit_fusion_data, args=(request.sid, symbol))
            thread.daemon = True
            thread.start()
    
    def _emit_fusion_data(self, session_id, symbol):
        """Emit fusion data every 100ms"""
        while session_id in self.active_subscriptions:
            try:
                # Get latest fusion data from backend
                fusion_data = self.fusion_engine.get_latest(symbol)
                
                # Emit to specific client
                self.socketio.emit('fusion_update', {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'price': {
                        'open': fusion_data.price.open,
                        'high': fusion_data.price.high,
                        'low': fusion_data.price.low,
                        'close': fusion_data.price.close,
                        'volume': fusion_data.price.volume
                    },
                    'sentiment': {
                        'score': fusion_data.sentiment.score,
                        'article_count': fusion_data.sentiment.article_count,
                        'latest_headline': fusion_data.sentiment.latest_headline
                    },
                    'events': [
                        {
                            'time': event.time,
                            'title': event.title,
                            'impact': event.impact,
                            'actual': event.actual,
                            'forecast': event.forecast
                        }
                        for event in fusion_data.events
                    ],
                    'sync_status': fusion_data.sync_status  # 'synced' | 'delayed' | 'stale'
                }, room=session_id)
                
                # Sleep 100ms (10 updates per second)
                time.sleep(0.1)
                
            except Exception as e:
                print(f'Error emitting fusion data: {e}')
                break

# Initialize in app.py
from trading_agent.fusion import InputFusionEngine
fusion_engine = InputFusionEngine()
ws_server = WebSocketServer(socketio, fusion_engine)
ws_server.start()
```

#### Step 1.3: Mock Data Generator (for testing without live market data)

```python
# backend/mock_fusion_data.py
import random
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta

@dataclass
class MockPriceData:
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class MockSentimentData:
    score: float  # -1.0 to 1.0
    article_count: int
    latest_headline: str

@dataclass
class MockEconomicEvent:
    time: str
    title: str
    impact: str  # 'H' | 'M' | 'L'
    actual: float
    forecast: float

class MockFusionEngine:
    """Mock fusion engine for testing without real market data"""
    
    def __init__(self):
        self.last_price = 1.0850  # EUR/USD starting price
        self.price_history = []
        
    def get_latest(self, symbol: str) -> dict:
        """Generate mock fusion data"""
        
        # Generate realistic price movement
        change = random.uniform(-0.0005, 0.0005)
        self.last_price += change
        
        open_price = self.last_price - random.uniform(0, 0.0002)
        high_price = self.last_price + random.uniform(0, 0.0003)
        low_price = self.last_price - random.uniform(0, 0.0003)
        close_price = self.last_price
        
        price = MockPriceData(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=random.randint(1000, 5000)
        )
        
        # Generate sentiment (correlated with price movement)
        sentiment_score = 0.5 + (change * 1000)  # Slight correlation
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        sentiment = MockSentimentData(
            score=sentiment_score,
            article_count=random.randint(10, 50),
            latest_headline=self._generate_headline(sentiment_score)
        )
        
        # Generate economic events (occasionally)
        events = []
        if random.random() < 0.1:  # 10% chance of event
            events.append(MockEconomicEvent(
                time=datetime.now().isoformat(),
                title=random.choice(['NFP', 'CPI', 'Fed Rate Decision', 'GDP']),
                impact=random.choice(['H', 'M', 'L']),
                actual=random.uniform(1.0, 3.0),
                forecast=random.uniform(1.0, 3.0)
            ))
        
        # Calculate sync status
        sync_status = 'synced'  # Simplified for mock
        if random.random() < 0.05:  # 5% chance of delay
            sync_status = 'delayed'
        
        return type('FusionData', (), {
            'price': price,
            'sentiment': sentiment,
            'events': events,
            'sync_status': sync_status
        })
    
    def _generate_headline(self, sentiment: float) -> str:
        if sentiment > 0.3:
            return random.choice([
                'EUR/USD rallies on strong EU data',
                'Dollar weakens amid Fed policy shift',
                'Euro gains on positive economic outlook'
            ])
        elif sentiment < -0.3:
            return random.choice([
                'EUR/USD falls on weak EU growth',
                'Dollar strengthens on hawkish Fed',
                'Euro under pressure from economic concerns'
            ])
        else:
            return random.choice([
                'EUR/USD consolidates in narrow range',
                'Mixed signals keep pair range-bound',
                'Traders await key economic data'
            ])
```

---

### Part 2: Frontend React Setup

#### Step 2.1: Initialize Vite Project

```bash
# Create React project with Vite
npm create vite@latest frontend -- --template react-ts

cd frontend

# Install dependencies
npm install

# Install UI libraries
npm install zustand socket.io-client recharts d3 @headlessui/react
npm install -D tailwindcss postcss autoprefixer
npm install react-router-dom @tanstack/react-query date-fns

# Initialize TailwindCSS
npx tailwindcss init -p
```

#### Step 2.2: TailwindCSS Configuration

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b',
      }
    },
  },
  plugins: [],
}
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles */
body {
  @apply bg-gray-50 text-gray-900;
}

.card {
  @apply bg-white rounded-lg shadow-sm p-4 border border-gray-200;
}

.btn-primary {
  @apply bg-primary text-white px-4 py-2 rounded-md hover:bg-green-600 transition;
}

.btn-danger {
  @apply bg-danger text-white px-4 py-2 rounded-md hover:bg-red-600 transition;
}
```

#### Step 2.3: Zustand Store for Real-time Data

```typescript
// frontend/src/stores/fusionStore.ts
import create from 'zustand';
import { io, Socket } from 'socket.io-client';

interface OHLCV {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface SentimentData {
  timestamp: string;
  score: number;
  article_count: number;
  latest_headline: string;
}

interface EconomicEvent {
  time: string;
  title: string;
  impact: 'H' | 'M' | 'L';
  actual: number;
  forecast: number;
}

interface FusionState {
  // Connection
  socket: Socket | null;
  isConnected: boolean;
  
  // Data buffers (circular, max 1000 items)
  priceBuffer: OHLCV[];
  sentimentBuffer: SentimentData[];
  eventBuffer: EconomicEvent[];
  
  // Sync status
  syncStatus: 'synced' | 'delayed' | 'stale';
  
  // Actions
  connectWebSocket: (symbol: string) => void;
  disconnectWebSocket: () => void;
  addPriceData: (data: OHLCV) => void;
  addSentimentData: (data: SentimentData) => void;
  addEvent: (event: EconomicEvent) => void;
  updateSyncStatus: (status: 'synced' | 'delayed' | 'stale') => void;
}

export const useFusionStore = create<FusionState>((set, get) => ({
  // Initial state
  socket: null,
  isConnected: false,
  priceBuffer: [],
  sentimentBuffer: [],
  eventBuffer: [],
  syncStatus: 'synced',
  
  // Connect to WebSocket
  connectWebSocket: (symbol: string) => {
    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });
    
    socket.on('connect', () => {
      console.log('WebSocket connected');
      set({ isConnected: true });
      
      // Subscribe to fusion data
      socket.emit('subscribe_fusion', { symbol });
    });
    
    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      set({ isConnected: false });
    });
    
    socket.on('fusion_update', (data) => {
      const state = get();
      
      // Add price data
      state.addPriceData({
        timestamp: data.timestamp,
        open: data.price.open,
        high: data.price.high,
        low: data.price.low,
        close: data.price.close,
        volume: data.price.volume
      });
      
      // Add sentiment data
      state.addSentimentData({
        timestamp: data.timestamp,
        score: data.sentiment.score,
        article_count: data.sentiment.article_count,
        latest_headline: data.sentiment.latest_headline
      });
      
      // Add events
      data.events.forEach((event: EconomicEvent) => {
        state.addEvent(event);
      });
      
      // Update sync status
      state.updateSyncStatus(data.sync_status);
    });
    
    set({ socket });
  },
  
  // Disconnect WebSocket
  disconnectWebSocket: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      set({ socket: null, isConnected: false });
    }
  },
  
  // Add price data (circular buffer, max 1000)
  addPriceData: (data: OHLCV) => {
    set(state => ({
      priceBuffer: [...state.priceBuffer, data].slice(-1000)
    }));
  },
  
  // Add sentiment data (circular buffer, max 500)
  addSentimentData: (data: SentimentData) => {
    set(state => ({
      sentimentBuffer: [...state.sentimentBuffer, data].slice(-500)
    }));
  },
  
  // Add economic event (circular buffer, max 100)
  addEvent: (event: EconomicEvent) => {
    set(state => ({
      eventBuffer: [...state.eventBuffer, event].slice(-100)
    }));
  },
  
  // Update sync status
  updateSyncStatus: (status: 'synced' | 'delayed' | 'stale') => {
    set({ syncStatus: status });
  }
}));
```

---

### Part 3: Live Dashboard Components

#### Step 3.1: Main Dashboard Layout

```tsx
// frontend/src/pages/LiveDashboard.tsx
import React, { useEffect } from 'react';
import { useFusionStore } from '../stores/fusionStore';
import PriceChartPanel from '../components/LiveDashboard/PriceChartPanel';
import SentimentPanel from '../components/LiveDashboard/SentimentPanel';
import EconomicEventsPanel from '../components/LiveDashboard/EconomicEventsPanel';
import SyncIndicator from '../components/LiveDashboard/SyncIndicator';
import DecisionLogTable from '../components/INoT/DecisionLogTable';

export default function LiveDashboard() {
  const { connectWebSocket, disconnectWebSocket, isConnected } = useFusionStore();
  
  useEffect(() => {
    // Connect on mount
    connectWebSocket('EURUSD');
    
    // Cleanup on unmount
    return () => {
      disconnectWebSocket();
    };
  }, []);
  
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Live Trading Dashboard</h1>
          <SyncIndicator />
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </header>
      
      {/* Main Content: 3-Panel Grid */}
      <div className="flex-1 grid grid-cols-3 gap-4 p-6 overflow-hidden">
        <div className="card">
          <PriceChartPanel />
        </div>
        
        <div className="card">
          <SentimentPanel />
        </div>
        
        <div className="card">
          <EconomicEventsPanel />
        </div>
      </div>
      
      {/* Bottom: INoT Decision Log */}
      <div className="h-64 bg-white border-t border-gray-200">
        <DecisionLogTable />
      </div>
    </div>
  );
}
```

#### Step 3.2: Price Chart Panel (Recharts)

```tsx
// frontend/src/components/LiveDashboard/PriceChartPanel.tsx
import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useFusionStore } from '../../stores/fusionStore';
import { format } from 'date-fns';

export default function PriceChartPanel() {
  const { priceBuffer } = useFusionStore();
  
  // Format data for Recharts
  const chartData = priceBuffer.map(item => ({
    time: format(new Date(item.timestamp), 'HH:mm:ss'),
    price: item.close,
    volume: item.volume
  }));
  
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">EUR/USD Price</h2>
        <span className="text-sm text-gray-500">
          Last: {priceBuffer[priceBuffer.length - 1]?.close.toFixed(5) || '—'}
        </span>
      </div>
      
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis 
              dataKey="time" 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => value.substring(0, 5)}
            />
            <YAxis 
              domain={['dataMin - 0.0005', 'dataMax + 0.0005']}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => value.toFixed(5)}
            />
            <Tooltip 
              contentStyle={{ background: '#fff', border: '1px solid #ddd' }}
              formatter={(value: number) => value.toFixed(5)}
            />
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke="#10b981" 
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* Volume Bar Chart (simplified) */}
      <div className="h-16 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis dataKey="time" hide />
            <YAxis hide />
            <Line 
              type="monotone" 
              dataKey="volume" 
              stroke="#6b7280" 
              strokeWidth={1}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

#### Step 3.3: Sentiment Panel

```tsx
// frontend/src/components/LiveDashboard/SentimentPanel.tsx
import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useFusionStore } from '../../stores/fusionStore';
import { format } from 'date-fns';

export default function SentimentPanel() {
  const { sentimentBuffer } = useFusionStore();
  
  const chartData = sentimentBuffer.map(item => ({
    time: format(new Date(item.timestamp), 'HH:mm:ss'),
    score: item.score,
    article_count: item.article_count
  }));
  
  const latestSentiment = sentimentBuffer[sentimentBuffer.length - 1];
  
  // Color based on sentiment
  const getSentimentColor = (score: number) => {
    if (score > 0.3) return 'text-green-600';
    if (score < -0.3) return 'text-red-600';
    return 'text-yellow-600';
  };
  
  const getSentimentLabel = (score: number) => {
    if (score > 0.3) return 'Bullish';
    if (score < -0.3) return 'Bearish';
    return 'Neutral';
  };
  
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Sentiment</h2>
        {latestSentiment && (
          <span className={`text-sm font-medium ${getSentimentColor(latestSentiment.score)}`}>
            {getSentimentLabel(latestSentiment.score)}
          </span>
        )}
      </div>
      
      {/* Sentiment Score Chart */}
      <div className="flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis 
              dataKey="time" 
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => value.substring(0, 5)}
            />
            <YAxis 
              domain={[-1, 1]}
              ticks={[-1, -0.5, 0, 0.5, 1]}
              tick={{ fontSize: 12 }}
            />
            <Tooltip contentStyle={{ background: '#fff', border: '1px solid #ddd' }} />
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <ReferenceLine y={0.3} stroke="#10b981" strokeDasharray="2 2" strokeOpacity={0.3} />
            <ReferenceLine y={-0.3} stroke="#ef4444" strokeDasharray="2 2" strokeOpacity={0.3} />
            <Line 
              type="monotone" 
              dataKey="score" 
              stroke="#6366f1" 
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {/* Article Ticker */}
      <div className="mt-4 space-y-2">
        <h3 className="text-sm font-medium text-gray-700">Latest News</h3>
        <div className="space-y-1">
          {sentimentBuffer.slice(-5).reverse().map((item, idx) => (
            <div key={idx} className="text-xs text-gray-600 truncate">
              • {item.latest_headline}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## 🧪 Testing Strategy

### Unit Tests (Vitest)

```typescript
// frontend/src/stores/fusionStore.test.ts
import { renderHook, act } from '@testing-library/react';
import { useFusionStore } from './fusionStore';

describe('FusionStore', () => {
  it('should add price data to buffer', () => {
    const { result } = renderHook(() => useFusionStore());
    
    act(() => {
      result.current.addPriceData({
        timestamp: '2024-01-01T00:00:00Z',
        open: 1.0850,
        high: 1.0855,
        low: 1.0845,
        close: 1.0852,
        volume: 1000
      });
    });
    
    expect(result.current.priceBuffer).toHaveLength(1);
    expect(result.current.priceBuffer[0].close).toBe(1.0852);
  });
  
  it('should maintain circular buffer max size', () => {
    const { result } = renderHook(() => useFusionStore());
    
    // Add 1500 items (should keep only last 1000)
    act(() => {
      for (let i = 0; i < 1500; i++) {
        result.current.addPriceData({
          timestamp: `2024-01-01T00:00:${i}Z`,
          open: 1.0850,
          high: 1.0855,
          low: 1.0845,
          close: 1.0852,
          volume: 1000
        });
      }
    });
    
    expect(result.current.priceBuffer).toHaveLength(1000);
  });
});
```

### E2E Tests (Playwright)

```typescript
// tests/e2e/live-dashboard.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Live Dashboard', () => {
  test('should connect to WebSocket and display data', async ({ page }) => {
    await page.goto('http://localhost:3000/dashboard');
    
    // Wait for WebSocket connection
    await page.waitForSelector('.bg-green-500'); // Connection indicator
    
    // Verify chart updates
    await page.waitForTimeout(1000); // Wait for data
    const chartExists = await page.locator('svg.recharts-surface').count();
    expect(chartExists).toBeGreaterThan(0);
    
    // Verify sync indicator
    const syncStatus = await page.locator('[data-testid="sync-indicator"]').textContent();
    expect(['synced', 'delayed', 'stale']).toContain(syncStatus);
  });
  
  test('should open decision detail modal on click', async ({ page }) => {
    await page.goto('http://localhost:3000/dashboard');
    
    // Wait for decision log to populate
    await page.waitForSelector('table tbody tr', { timeout: 5000 });
    
    // Click first row
    await page.click('table tbody tr:first-child');
    
    // Verify modal opens
    await expect(page.locator('[role="dialog"]')).toBeVisible();
    
    // Verify agent debates visible
    await expect(page.locator('text=Agent A')).toBeVisible();
  });
});
```

---

## 🚀 Deployment Guide

### Docker Configuration

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ../backend
      dockerfile: ../docker/Dockerfile.backend
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///trading_agent.db
    volumes:
      - ../backend:/app
      - sqlite_data:/app/data
    restart: unless-stopped
  
  frontend:
    build:
      context: ../frontend
      dockerfile: ../docker/Dockerfile.frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  sqlite_data:
```

```dockerfile
# docker/Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
```

```dockerfile
# docker/Dockerfile.frontend
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
# docker/nginx.conf
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # React Router support
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://backend:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket support
    location /socket.io/ {
        proxy_pass http://backend:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📊 Success Metrics

### Technical KPIs

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **WebSocket Latency** | <100ms P95 | Server-side logging |
| **UI Render Time** | <30ms P95 | React DevTools Profiler |
| **Chart FPS** | >30 FPS | Chrome Performance tab |
| **API Response Time** | <200ms | Flask logging |
| **Test Coverage** | >80% | Vitest + Istanbul |

### User Experience KPIs

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| **Decision Log Usage** | >60% of users | Google Analytics events |
| **Avg Session Duration** | >30 min | Analytics |
| **Chart Interaction Rate** | >40% users | Click tracking |
| **Modal Open Rate** | >50% of sessions | Event tracking |

---

## 🎯 Milestones & Checkpoints

### Week 1 Checkpoint
- [ ] WebSocket server emitting mock data
- [ ] React app connected and displaying connection status
- [ ] Basic 3-panel layout rendered

### Week 2 Checkpoint
- [ ] All 3 panels displaying live data
- [ ] Sync indicator functional
- [ ] Charts updating smoothly (<30ms render)

### Week 3 Checkpoint
- [ ] Backtest API endpoints functional
- [ ] Equity curve + metrics displayed
- [ ] Trade list filterable

### Week 4 Checkpoint (MVP Complete)
- [ ] Decision Modal with full explanations
- [ ] Risk controls functional
- [ ] E2E tests passing
- [ ] Docker deployment working

---

## 📚 Additional Resources

**Documentation:**
- [Flask-SocketIO Docs](https://flask-socketio.readthedocs.io/)
- [Recharts API Reference](https://recharts.org/en-US/api)
- [Zustand Guide](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [Playwright Testing](https://playwright.dev/docs/intro)

**Example Code:**
- [Real-time Dashboard Example](https://github.com/socketio/socket.io/tree/main/examples/chat)
- [Recharts Stock Chart](https://recharts.org/en-US/examples/SimpleLineChart)
- [Zustand WebSocket Integration](https://github.com/pmndrs/zustand/discussions/1082)

---

**Created:** 2025-11-03  
**Version:** 1.0  
**Status:** ✅ Ready for Implementation  
**Next Step:** Start Sprint 1 (Backend WebSocket Server)
