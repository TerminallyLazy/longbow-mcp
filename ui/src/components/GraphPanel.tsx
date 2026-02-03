import { useState, useCallback, useRef, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { Play, Plus, X } from 'lucide-react';
import { Memory, GraphData, GraphNode, GraphLink } from '../hooks/useMemoryBridge';

interface GraphPanelProps {
  memories: Memory[];
  graphData: GraphData;
  onTraverse: (startId: string, maxHops?: number, incoming?: boolean, decay?: number, weighted?: boolean) => void;
  onAddEdge: (sourceId: string, targetId: string, predicate?: string, weight?: number) => void;
}

const PREDICATES = ['related_to', 'causes', 'follows', 'contradicts', 'supports', 'extends'];

export function GraphPanel({ memories, graphData, onTraverse, onAddEdge }: GraphPanelProps) {
  const graphRef = useRef<ForceGraphMethods | undefined>();
  const [startNodeId, setStartNodeId] = useState('');
  const [maxHops, setMaxHops] = useState(2);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Edge form state
  const [showEdgeForm, setShowEdgeForm] = useState(false);
  const [edgeSource, setEdgeSource] = useState('');
  const [edgeTarget, setEdgeTarget] = useState('');
  const [edgePredicate, setEdgePredicate] = useState('related_to');
  const [edgeWeight, setEdgeWeight] = useState(1.0);

  const handleTraverse = useCallback(() => {
    if (!startNodeId) return;
    onTraverse(startNodeId, maxHops);
  }, [startNodeId, maxHops, onTraverse]);

  const handleAddEdge = useCallback(() => {
    if (!edgeSource || !edgeTarget) return;
    onAddEdge(edgeSource, edgeTarget, edgePredicate, edgeWeight);
    setShowEdgeForm(false);
    setEdgeSource('');
    setEdgeTarget('');
    setEdgePredicate('related_to');
    setEdgeWeight(1.0);
  }, [edgeSource, edgeTarget, edgePredicate, edgeWeight, onAddEdge]);

  // Build data: always show all memories as nodes, overlay traversal edges
  const forceData = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();

    // Base layer: every memory is a node
    for (const m of memories) {
      nodeMap.set(m.id, {
        id: m.id,
        content: m.content,
        score: 0,
        isStart: false,
      });
    }

    // Overlay traversal results (marks start node, updates scores)
    for (const n of graphData.nodes) {
      nodeMap.set(n.id, { ...n });
    }

    return {
      nodes: Array.from(nodeMap.values()).map(n => ({ ...n })),
      links: graphData.links.map(l => ({ ...l })),
    };
  }, [memories, graphData]);

  // Set of node IDs connected to hovered node
  const hoveredNeighborLinks = useMemo(() => {
    if (!hoveredNode) return new Set<string>();
    const linkIds = new Set<string>();
    for (const l of graphData.links) {
      const src = typeof l.source === 'object' ? (l.source as GraphNode).id : l.source;
      const tgt = typeof l.target === 'object' ? (l.target as GraphNode).id : l.target;
      if (src === hoveredNode || tgt === hoveredNode) {
        linkIds.add(`${src}->${tgt}`);
      }
    }
    return linkIds;
  }, [hoveredNode, graphData.links]);

  const nodeCanvasObject = useCallback((node: Record<string, unknown>, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const gNode = node as unknown as GraphNode & { x: number; y: number };
    const label = gNode.content.length > 30 ? gNode.content.slice(0, 30) + '...' : gNode.content;
    const fontSize = 12 / globalScale;
    const nodeRadius = gNode.isStart ? 8 : 5;
    const isHovered = hoveredNode === gNode.id;

    // Glow effect
    if (isHovered || gNode.isStart) {
      ctx.beginPath();
      ctx.arc(gNode.x, gNode.y, nodeRadius + 4, 0, 2 * Math.PI);
      ctx.fillStyle = gNode.isStart
        ? 'rgba(255, 255, 33, 0.2)'
        : 'rgba(94, 247, 166, 0.25)';
      ctx.fill();
    }

    // Node circle
    ctx.beginPath();
    ctx.arc(gNode.x, gNode.y, nodeRadius, 0, 2 * Math.PI);
    ctx.fillStyle = gNode.isStart ? '#FFFF21' : '#5EF7A6';
    ctx.fill();

    // Label
    ctx.font = `${fontSize}px "Space Grotesk", monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
    ctx.fillText(label, gNode.x, gNode.y + nodeRadius + 2);
  }, [hoveredNode]);

  const linkColor = useCallback((link: Record<string, unknown>) => {
    const l = link as unknown as GraphLink;
    const src = typeof l.source === 'object' ? (l.source as unknown as GraphNode).id : l.source;
    const tgt = typeof l.target === 'object' ? (l.target as unknown as GraphNode).id : l.target;
    const key = `${src}->${tgt}`;
    return hoveredNeighborLinks.has(key) ? 'rgba(94, 247, 166, 0.7)' : 'rgba(255, 255, 255, 0.15)';
  }, [hoveredNeighborLinks]);

  const selectedMemory = selectedNode
    ? memories.find(m => m.id === selectedNode.id)
    : null;

  return (
    <div className="h-full flex flex-col">
      {/* Controls bar */}
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <select
          value={startNodeId}
          onChange={e => setStartNodeId(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white
                     focus:outline-none focus:border-emerald/50 min-w-[200px]"
        >
          <option value="">Select start node...</option>
          {memories.map(m => (
            <option key={m.id} value={m.id}>
              {m.content.slice(0, 50)}{m.content.length > 50 ? '...' : ''}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <label className="text-xs text-white/50">Hops:</label>
          <input
            type="range"
            min={1}
            max={5}
            value={maxHops}
            onChange={e => setMaxHops(Number(e.target.value))}
            className="w-20 accent-emerald"
          />
          <span className="text-xs text-white/70 w-4">{maxHops}</span>
        </div>

        <button
          onClick={handleTraverse}
          disabled={!startNodeId}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald/20 text-emerald
                     hover:bg-emerald/30 disabled:opacity-30 disabled:cursor-not-allowed
                     transition-all text-sm font-medium"
        >
          <Play className="w-3.5 h-3.5" />
          Traverse
        </button>

        <button
          onClick={() => setShowEdgeForm(!showEdgeForm)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                     ${showEdgeForm
                       ? 'bg-cyber-lime/20 text-cyber-lime'
                       : 'bg-white/5 text-white/60 hover:bg-white/10 hover:text-white'
                     }`}
        >
          {showEdgeForm ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
          {showEdgeForm ? 'Cancel' : 'Add Edge'}
        </button>
      </div>

      {/* Edge creation form */}
      {showEdgeForm && (
        <div className="flex items-center gap-3 mb-3 p-3 rounded-lg bg-white/5 border border-white/10 flex-wrap">
          <select
            value={edgeSource}
            onChange={e => setEdgeSource(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white
                       focus:outline-none focus:border-emerald/50 min-w-[160px]"
          >
            <option value="">Source...</option>
            {memories.map(m => (
              <option key={m.id} value={m.id}>
                {m.content.slice(0, 40)}{m.content.length > 40 ? '...' : ''}
              </option>
            ))}
          </select>

          <span className="text-white/30 text-xs">--&gt;</span>

          <select
            value={edgeTarget}
            onChange={e => setEdgeTarget(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white
                       focus:outline-none focus:border-emerald/50 min-w-[160px]"
          >
            <option value="">Target...</option>
            {memories.map(m => (
              <option key={m.id} value={m.id}>
                {m.content.slice(0, 40)}{m.content.length > 40 ? '...' : ''}
              </option>
            ))}
          </select>

          <select
            value={edgePredicate}
            onChange={e => setEdgePredicate(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white
                       focus:outline-none focus:border-emerald/50"
          >
            {PREDICATES.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>

          <div className="flex items-center gap-1">
            <label className="text-xs text-white/50">W:</label>
            <input
              type="number"
              min={0}
              max={10}
              step={0.1}
              value={edgeWeight}
              onChange={e => setEdgeWeight(Number(e.target.value))}
              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-sm text-white
                         focus:outline-none focus:border-emerald/50 w-16"
            />
          </div>

          <button
            onClick={handleAddEdge}
            disabled={!edgeSource || !edgeTarget}
            className="px-4 py-1.5 rounded-lg bg-cyber-lime/20 text-cyber-lime text-sm font-medium
                       hover:bg-cyber-lime/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            Create
          </button>
        </div>
      )}

      {/* Graph canvas */}
      <div className="flex-1 relative rounded-lg overflow-hidden border border-white/5 min-h-0">
        {memories.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-white/30">
            <svg className="w-12 h-12 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
            </svg>
            <span className="text-sm">No memories yet</span>
            <span className="text-xs mt-1">Add memories first, then explore their graph</span>
          </div>
        ) : (
          <ForceGraph2D
            ref={graphRef as React.MutableRefObject<ForceGraphMethods | undefined>}
            graphData={forceData}
            nodeId="id"
            backgroundColor="rgba(0,0,0,0)"
            nodeCanvasObject={nodeCanvasObject}
            nodePointerAreaPaint={(node, color, ctx) => {
              const gNode = node as unknown as GraphNode & { x: number; y: number };
              ctx.beginPath();
              ctx.arc(gNode.x, gNode.y, 10, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            linkColor={linkColor}
            linkWidth={(link) => {
              const l = link as unknown as GraphLink;
              const src = typeof l.source === 'object' ? (l.source as unknown as GraphNode).id : l.source;
              const tgt = typeof l.target === 'object' ? (l.target as unknown as GraphNode).id : l.target;
              return hoveredNeighborLinks.has(`${src}->${tgt}`) ? 2 : 1;
            }}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={0.9}
            onNodeClick={(node) => {
              setSelectedNode(node as unknown as GraphNode);
            }}
            onNodeHover={(node) => {
              setHoveredNode(node ? (node as unknown as GraphNode).id : null);
            }}
            cooldownTicks={100}
            warmupTicks={50}
          />
        )}
      </div>

      {/* Node detail card */}
      {selectedNode && (
        <div className="mt-3 p-4 rounded-lg bg-white/5 border border-white/10">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${selectedNode.isStart ? 'bg-cyber-lime' : 'bg-emerald'}`} />
              <span className="text-xs text-white/50 font-mono">{selectedNode.id.slice(0, 16)}...</span>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="p-1 rounded hover:bg-white/10 text-white/40 hover:text-white transition-all"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-sm text-white/80 leading-relaxed">{selectedNode.content}</p>
          {selectedMemory && (
            <div className="mt-2 flex items-center gap-4 text-xs text-white/40">
              <span>Client: {selectedMemory.client_id}</span>
              <span>Created: {new Date(selectedMemory.created_at).toLocaleString()}</span>
              {Object.keys(selectedMemory.metadata).length > 0 && (
                <span>Meta: {JSON.stringify(selectedMemory.metadata)}</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default GraphPanel;
