import { useEffect } from 'react';
import { useFusionStore } from '../stores/fusionStore';

export const useWebSocket = (symbol: string) => {
  const { connect, disconnect, connectionStatus, latencyMs } = useFusionStore();

  useEffect(() => {
    connect(symbol);
    return () => disconnect();
  }, [connect, disconnect, symbol]);

  return { connectionStatus, latencyMs };
};
