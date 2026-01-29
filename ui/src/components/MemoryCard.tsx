import { useState } from 'react';
import { Brain, Calendar, Hash, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { Memory } from '../hooks/useMemoryBridge';

interface MemoryCardProps {
  memory: Memory;
  score?: number;
  onDelete?: () => void;
}

export function MemoryCard({ memory, score, onDelete }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);

  const formattedDate = new Date(memory.created_at).toLocaleString();
  const isLongContent = memory.content.length > 150;
  const displayContent = isExpanded ? memory.content : memory.content.slice(0, 150);

  return (
    <div className="glass-panel rounded-xl p-5 hover:border-emerald/30 transition-all duration-300 group animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald/10 flex items-center justify-center">
            <Brain className="w-5 h-5 text-emerald" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-white/40">
                #{memory.id.slice(0, 8)}
              </span>
              {score !== undefined && (
                <span className="px-2 py-0.5 rounded-full bg-cyber-lime/20 text-cyber-lime text-xs font-mono">
                  {(score * 100).toFixed(1)}%
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Calendar className="w-3 h-3 text-white/30" />
              <span className="text-xs text-white/40">{formattedDate}</span>
            </div>
          </div>
        </div>

        {onDelete && (
          <button
            onClick={onDelete}
            className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-red-500/20 hover:text-red-400 transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="relative">
        <p className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">
          {displayContent}
          {!isExpanded && isLongContent && '...'}
        </p>

        {isLongContent && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 flex items-center gap-1 text-xs text-emerald hover:text-emerald/80 transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                Show more
              </>
            )}
          </button>
        )}
      </div>

      {/* Metadata toggle */}
      {Object.keys(memory.metadata).length > 0 && (
        <button
          onClick={() => setShowMetadata(!showMetadata)}
          className="mt-3 flex items-center gap-2 text-xs text-white/40 hover:text-emerald transition-colors"
        >
          <Hash className="w-3 h-3" />
          {showMetadata ? 'Hide metadata' : 'Show metadata'}
        </button>
      )}

      {/* Metadata display */}
      {showMetadata && Object.keys(memory.metadata).length > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-white/5 border border-white/10">
          <pre className="text-xs text-white/60 font-mono overflow-x-auto">
            {JSON.stringify(memory.metadata, null, 2)}
          </pre>
        </div>
      )}

      {/* Client ID badge */}
      <div className="mt-3 pt-3 border-t border-white/10 flex justify-between items-center">
        <span className="text-xs text-white/30">Client</span>
        <span className="px-2 py-1 rounded bg-white/5 text-xs font-mono text-white/50">
          {memory.client_id}
        </span>
      </div>
    </div>
  );
}

export default MemoryCard;
