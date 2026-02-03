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

export interface GraphNode {
  id: string;
  content: string;
  score: number;
  isStart: boolean;
}

export interface GraphLink {
  source: string;
  target: string;
  predicate: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
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
  const memoriesRef = useRef<Memory[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });

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

            case 'traverse_results':
              if (message.data && typeof message.data === 'object') {
                const tData = message.data as { start_id: string; nodes: Array<Record<string, unknown> | null>; hops: number };
                const startId = tData.start_id;
                const nodeMap = new Map<string, GraphNode>();

                // Always include the start node
                const startMem = memoriesRef.current.find(m => m.id === startId);
                nodeMap.set(startId, {
                  id: startId,
                  content: startMem?.content ?? startId.slice(0, 8),
                  score: 1.0,
                  isStart: true,
                });

                // Filter out null entries (Longbow returns null when no edges exist)
                const validNodes = (tData.nodes || []).filter((n): n is Record<string, unknown> => n != null);

                // Each traversal result is an SPO triple: {subject, predicate, object, weight, score}
                // After server-side translation, subject/object are now memory UUIDs
                const links: GraphLink[] = [];
                for (const n of validNodes) {
                  const subj = String(n.subject ?? n.id ?? n.node_id ?? '');
                  const obj = String(n.object ?? '');

                  // Register both endpoints as graph nodes
                  for (const nid of [subj, obj]) {
                    if (nid && !nodeMap.has(nid)) {
                      const mem = memoriesRef.current.find(m => m.id === nid);
                      nodeMap.set(nid, {
                        id: nid,
                        content: mem?.content ?? nid.slice(0, 8),
                        score: Number(n.score ?? 0),
                        isStart: false,
                      });
                    }
                  }

                  // Build directed link
                  if (subj && obj && subj !== obj) {
                    links.push({
                      source: subj,
                      target: obj,
                      predicate: String(n.predicate ?? 'related_to'),
                      weight: Number(n.weight ?? 1),
                    });
                  }
                }

                setGraphData({ nodes: Array.from(nodeMap.values()), links });
              }
              break;

            case 'edge_added':
              if (message.data && typeof message.data === 'object') {
                const edge = message.data as { source_id: string; target_id: string; predicate: string; weight: number };
                setGraphData(prev => {
                  // Add target node if missing
                  const nodes = [...prev.nodes];
                  if (!nodes.find(n => n.id === edge.target_id)) {
                    const mem = memoriesRef.current.find(m => m.id === edge.target_id);
                    nodes.push({
                      id: edge.target_id,
                      content: mem?.content ?? edge.target_id.slice(0, 8),
                      score: 0,
                      isStart: false,
                    });
                  }
                  if (!nodes.find(n => n.id === edge.source_id)) {
                    const mem = memoriesRef.current.find(m => m.id === edge.source_id);
                    nodes.push({
                      id: edge.source_id,
                      content: mem?.content ?? edge.source_id.slice(0, 8),
                      score: 0,
                      isStart: false,
                    });
                  }
                  return {
                    nodes,
                    links: [...prev.links, {
                      source: edge.source_id,
                      target: edge.target_id,
                      predicate: edge.predicate,
                      weight: edge.weight,
                    }],
                  };
                });
              }
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

  const traverseGraph = useCallback((startId: string, maxHops: number = 2, incoming: boolean = false, decay: number = 0, weighted: boolean = true) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      action: 'traverse',
      start_id: startId,
      max_hops: maxHops,
      incoming,
      decay,
      weighted,
    }));
  }, []);

  const addEdge = useCallback((sourceId: string, targetId: string, predicate: string = 'related_to', weight: number = 1.0) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      action: 'add_edge',
      source_id: sourceId,
      target_id: targetId,
      predicate,
      weight,
    }));
  }, []);

  const refreshMemories = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ action: 'list_memories', limit: 50 }));
  }, []);

  // Keep memoriesRef in sync for use in WS handlers (avoids stale closure)
  useEffect(() => {
    memoriesRef.current = memories;
  }, [memories]);

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
    graphData,
    searchMemories,
    addMemory,
    deleteAllMemories,
    refreshMemories,
    traverseGraph,
    addEdge,
  };
}

export default useMemoryBridge;
