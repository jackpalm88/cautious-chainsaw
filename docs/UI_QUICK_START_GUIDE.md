# ⚡ UI Quick Start Guide

**Time to First Screen:** ~30 minutes  
**Prerequisites:** Python 3.11+, Node.js 20+, Git

---

## 🚀 Zero to Dashboard in 30 Minutes

### Step 1: Clone & Setup (5 min)

```bash
# Clone repo
git clone https://github.com/jackpalm88/cautious-chainsaw.git
cd cautious-chainsaw

# Create UI directories
mkdir -p backend/api backend/models
mkdir -p frontend/src/{pages,components,stores,hooks}
```

### Step 2: Backend Flask + SocketIO (10 min)

```bash
# Install backend dependencies
cd backend
pip install flask flask-socketio flask-cors python-socketio eventlet

# Create app.py
cat > app.py << 'EOF'
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import random
import time
from threading import Thread

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_status', {'status': 'connected'})

@socketio.on('subscribe_fusion')
def handle_subscribe(data):
    symbol = data.get('symbol', 'EURUSD')
    
    def emit_data():
        price = 1.0850
        while True:
            price += random.uniform(-0.0005, 0.0005)
            socketio.emit('fusion_update', {
                'timestamp': time.time(),
                'symbol': symbol,
                'price': {
                    'open': price - 0.0001,
                    'high': price + 0.0002,
                    'low': price - 0.0002,
                    'close': price,
                    'volume': random.randint(1000, 5000)
                },
                'sentiment': {
                    'score': random.uniform(-0.5, 0.5),
                    'article_count': random.randint(10, 50),
                    'latest_headline': 'EUR/USD market update'
                },
                'events': [],
                'sync_status': 'synced'
            })
            time.sleep(0.1)
    
    thread = Thread(target=emit_data)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
EOF

# Run backend
python app.py &
```

### Step 3: Frontend React + Vite (15 min)

```bash
# Create React app
cd ../
npm create vite@latest frontend -- --template react-ts
cd frontend

# Install dependencies
npm install
npm install zustand socket.io-client recharts tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Configure Tailwind
cat > tailwind.config.js << 'EOF'
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
EOF

# Add Tailwind to CSS
cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

# Create Zustand store
mkdir -p src/stores
cat > src/stores/fusionStore.ts << 'EOF'
import create from 'zustand';
import { io } from 'socket.io-client';

export const useFusionStore = create((set) => ({
  isConnected: false,
  priceData: [],
  
  connectWebSocket: () => {
    const socket = io('http://localhost:5000');
    
    socket.on('connect', () => {
      console.log('Connected');
      set({ isConnected: true });
      socket.emit('subscribe_fusion', { symbol: 'EURUSD' });
    });
    
    socket.on('fusion_update', (data) => {
      set((state) => ({
        priceData: [...state.priceData, {
          time: new Date(data.timestamp * 1000).toLocaleTimeString(),
          price: data.price.close
        }].slice(-100)
      }));
    });
  }
}));
EOF

# Create Dashboard component
mkdir -p src/pages
cat > src/pages/LiveDashboard.tsx << 'EOF'
import { useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { useFusionStore } from '../stores/fusionStore';

export default function LiveDashboard() {
  const { isConnected, priceData, connectWebSocket } = useFusionStore();
  
  useEffect(() => {
    connectWebSocket();
  }, []);
  
  return (
    <div className="h-screen bg-gray-50 p-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">Live Trading Dashboard</h1>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
        
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={priceData}>
              <XAxis dataKey="time" />
              <YAxis domain={['dataMin - 0.001', 'dataMax + 0.001']} />
              <Tooltip />
              <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        <div className="mt-4 text-sm text-gray-600">
          Latest Price: {priceData[priceData.length - 1]?.price.toFixed(5) || '—'}
        </div>
      </div>
    </div>
  );
}
EOF

# Update App.tsx
cat > src/App.tsx << 'EOF'
import LiveDashboard from './pages/LiveDashboard';

function App() {
  return <LiveDashboard />;
}

export default App;
EOF

# Run frontend
npm run dev
```

### Step 4: Open Browser

```bash
# Open http://localhost:5173
# You should see a live-updating price chart! 🎉
```

---

## ✅ What You Just Built

- ✅ **WebSocket Server** (Flask + python-socketio)
- ✅ **Real-time Price Stream** (100ms updates)
- ✅ **React Dashboard** (Live chart with Recharts)
- ✅ **State Management** (Zustand store)
- ✅ **Connection Status** (Visual indicator)

---

## 🎯 Next Steps

### Immediate (Today)
1. **Add Sentiment Panel**
   - Copy PriceChartPanel pattern
   - Display sentiment score (-1 to 1)
   - Show latest headlines

2. **Add Sync Indicator**
   - Calculate latency between streams
   - Show green/yellow/red status

### Tomorrow
3. **Economic Events Panel**
   - Timeline visualization
   - Impact indicators (H/M/L)

4. **Decision Log Table**
   - Bottom panel with last 20 decisions
   - Click row → open modal

### This Week
5. **Strategy Backtest Workbench**
   - New page `/backtest`
   - Strategy selector dropdown
   - Equity curve display

6. **INoT Decision Detail Modal**
   - 4-agent debate accordion
   - Confidence gauge
   - Context inputs

---

## 🔧 Troubleshooting

### Backend not running?
```bash
# Check if port 5000 is already in use
lsof -i :5000

# Kill process if needed
kill -9 <PID>

# Restart backend
cd backend && python app.py
```

### Frontend build errors?
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### WebSocket connection issues?
```bash
# Check CORS settings in backend/app.py
# Ensure cors_allowed_origins="*" is set

# Check browser console for errors
# Open DevTools → Network → WS tab
```

---

## 📊 Verify Everything Works

### Backend Health Check
```bash
curl http://localhost:5000/
# Should return Flask app response
```

### WebSocket Connection Test
```bash
# Open browser console
# Run:
const socket = io('http://localhost:5000');
socket.on('connect', () => console.log('Connected!'));
socket.emit('subscribe_fusion', { symbol: 'EURUSD' });
socket.on('fusion_update', (data) => console.log('Price:', data.price.close));
```

### Frontend Build Test
```bash
cd frontend
npm run build
# Should create dist/ folder with no errors
```

---

## 🎓 Learning Resources

**Completed:**
- [x] Flask WebSocket basics
- [x] React + Vite setup
- [x] Zustand state management
- [x] Recharts line chart

**Next:**
- [ ] [Flask-SocketIO Rooms](https://flask-socketio.readthedocs.io/en/latest/getting_started.html#rooms)
- [ ] [Recharts Composition](https://recharts.org/en-US/guide/composition)
- [ ] [React Query for API](https://tanstack.com/query/latest/docs/framework/react/quick-start)
- [ ] [Playwright E2E Testing](https://playwright.dev/docs/intro)

---

## 📁 Current Project Structure

```
cautious-chainsaw/
├── backend/
│   ├── app.py                  # ✅ Flask + SocketIO server
│   └── requirements.txt        # ✅ Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # ✅ Root component
│   │   ├── pages/
│   │   │   └── LiveDashboard.tsx  # ✅ Main dashboard
│   │   └── stores/
│   │       └── fusionStore.ts     # ✅ WebSocket + state
│   ├── package.json           # ✅ Dependencies
│   └── vite.config.ts         # ✅ Vite config
│
└── docs/
    ├── UI_ARCHITECTURE_INOT_ANALYSIS.md    # ✅ Strategic analysis
    ├── UI_IMPLEMENTATION_ROADMAP.md         # ✅ Detailed guide
    └── UI_QUICK_START_GUIDE.md              # ✅ This file
```

---

## 🚀 Deploy to Production

### Option 1: Docker Compose (Recommended)

```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    restart: unless-stopped
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped
EOF

# Build and run
docker-compose up -d

# Access at http://localhost:3000
```

### Option 2: Manual Deployment

```bash
# Backend (Gunicorn + eventlet)
cd backend
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app

# Frontend (Nginx)
cd frontend
npm run build
# Serve dist/ folder with Nginx or any static server
```

---

## 🎯 MVP Checklist (4 Weeks)

### Week 1 ✅ (Done Today!)
- [x] Backend WebSocket server
- [x] Frontend React + Vite setup
- [x] Live price chart
- [x] Connection status indicator

### Week 2 (Next)
- [ ] Add sentiment panel
- [ ] Add economic events panel
- [ ] Sync indicator (temporal alignment)
- [ ] Smooth out chart performance

### Week 3
- [ ] Strategy backtest API endpoints
- [ ] Backtest workbench UI
- [ ] Equity curve + metrics
- [ ] Trade list DataGrid

### Week 4
- [ ] INoT decision log table
- [ ] Decision detail modal
- [ ] Risk control center
- [ ] E2E tests + deployment

---

## 💡 Tips for Success

1. **Commit often**
   ```bash
   git add .
   git commit -m "feat: add live dashboard with price chart"
   git push origin main
   ```

2. **Test incrementally**
   - Don't wait until end to test
   - Verify each component works before moving on

3. **Use browser DevTools**
   - Network tab → WS tab (watch WebSocket messages)
   - Console (check for errors)
   - React DevTools (inspect component state)

4. **Start simple, iterate**
   - Get basic version working first
   - Add polish later (animations, error handling, etc.)

---

## 🆘 Need Help?

**Documentation:**
- [Full Architecture Analysis](./UI_ARCHITECTURE_INOT_ANALYSIS.md)
- [Detailed Roadmap](./UI_IMPLEMENTATION_ROADMAP.md)

**Code Examples:**
- Backend: `backend/app.py` (already created)
- Frontend: `frontend/src/pages/LiveDashboard.tsx` (already created)

**Community:**
- GitHub Issues: https://github.com/jackpalm88/cautious-chainsaw/issues
- Discord: [TBD]

---

**Created:** 2025-11-03  
**Version:** 1.0  
**Status:** ✅ Ready to Use  
**Time Investment:** 30 minutes to first dashboard  
**Next Step:** Add sentiment panel (15 min)

---

**Congratulations!** 🎉 You now have a working real-time trading dashboard. Keep going!
