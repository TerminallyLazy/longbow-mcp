import { useRef, useState, useCallback, useEffect } from 'react';

export interface Memory {
  id: string;
  content: string;
  embedding?: number[];
  metadata: Record<string, unknown>;
  created_at: string;
  client_id: string;
}

export interface SearchResult {
  memory: Memory;
  score: number;
}

export interface MemoryStats {
  total_memories: number;
  unique_clients: number;
  oldest_memory?: string;
  newest_memory?: string;
}

export interface BridgeMessage {
  type: string;
  timestamp?: string;
  data: unknown;
}

export function useMemoryBridge() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [stats, setStats] = useState<MemoryStats>({
    total_memories: 0,
    unique_clients: 0
  });
  const [memories, setMemories] = useState<Memory[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const connect = useCallback(() => {
    // Use relative WebSocket URL to work with nginx proxy
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Memory bridge connected');
        setIsConnected(true);

        // Request initial data
        ws.send(JSON.stringify({ action: 'get_stats' }));
        ws.send(JSON.stringify({ action: 'list_memories', limit: 50 }));
      };

      ws.onmessage = (event) => {
        try {
          const message: BridgeMessage = JSON.parse(event.data);

          switch (message.type) {
            case 'connected':
            case 'stats':
              if (message.data) {
                setStats(message.data as MemoryStats);
              }
              break;

            case 'memories_list':
              if (message.data && typeof message.data === 'object') {
                const data = message.data as { memories: Memory[]; total: number };
                setMemories(data.memories);
              }
              break;

            case 'search_results':
              if (message.data && typeof message.data === 'object') {
                const data = message.data as { results: SearchResult[]; query: string };
                setSearchResults(data.results);
                setIsSearching(false);
              }
              break;

            case 'memory_added':
              if (message.data && typeof message.data === 'object') {
                const newMemory = (message.data as { memory: Memory }).memory;
                setMemories(prev => [newMemory, ...prev]);
                // Refresh stats
                wsRef.current?.send(JSON.stringify({ action: 'get_stats' }));
              }
              break;

            case 'memories_deleted':
              setMemories([]);
              setSearchResults([]);
              wsRef.current?.send(JSON.stringify({ action: 'get_stats' }));
              break;

            case 'pong':
              break;

            default:
              console.log('Unknown message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to connect:', err);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
    setIsConnected(false);
  }, []);

  // Actions
  const searchMemories = useCallback((query: string, topK: number = 5) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('Bridge not connected');
      return;
    }

    setIsSearching(true);
    setSearchResults([]);

    wsRef.current.send(JSON.stringify({
      action: 'search',
      query,
      top_k: topK
    }));
  }, []);

  const addMemory = useCallback((content: string, metadata: Record<string, unknown> = {}, clientId: string = 'web-ui') => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('Bridge not connected');
      return;
    }

    wsRef.current.send(JSON.stringify({
      action: 'add_memory',
      content,
      metadata,
      client_id: clientId
    }));
  }, []);

  const deleteAllMemories = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('Bridge not connected');
      return;
    }

    if (confirm('Are you sure you want to delete all memories?')) {
      wsRef.current.send(JSON.stringify({ action: 'delete_all' }));
    }
  }, []);

  const refreshMemories = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: 'list_memories', limit: 50 }));
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Keepalive ping
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      wsRef.current?.send(JSON.stringify({ action: 'ping' }));
    }, 30000);

    return () => clearInterval(interval);
  }, [isConnected]);

  return {
    isConnected,
    stats,
    memories,
    searchResults,
    isSearching,
    searchMemories,
    addMemory,
    deleteAllMemories,
    refreshMemories
  };
}

export default useMemoryBridge;
