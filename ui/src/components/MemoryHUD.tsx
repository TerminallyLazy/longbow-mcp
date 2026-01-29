import { useState } from 'react';
import {
  Database,
  Users,
  Activity,
  RefreshCw,
  Trash2,
  Search,
  Plus,
  Zap,
  Wifi,
  WifiOff
} from 'lucide-react';
import { Memory, MemoryStats, SearchResult } from '../hooks/useMemoryBridge';
import MemoryCard from './MemoryCard';
import SearchPanel from './SearchPanel';
import AddMemoryForm from './AddMemoryForm';

interface MemoryHUDProps {
  isConnected: boolean;
  stats: MemoryStats;
  memories: Memory[];
  searchResults: SearchResult[];
  isSearching: boolean;
  onSearch: (query: string, topK?: number) => void;
  onAdd: (content: string, metadata: Record<string, unknown>) => void;
  onDeleteAll: () => void;
  onRefresh: () => void;
}

export function MemoryHUD({
  isConnected,
  stats,
  memories,
  searchResults,
  isSearching,
  onSearch,
  onAdd,
  onDeleteAll,
  onRefresh
}: MemoryHUDProps) {
  const [activeTab, setActiveTab] = useState<'all' | 'search' | 'add'>('all');

  return (
    <div className="h-full p-6 overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald/10 flex items-center justify-center glow-emerald">
              <Database className="w-5 h-5 text-emerald" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">MCP Memory</h1>
              <p className="text-xs text-white/40">Cross-client persistent memory</p>
            </div>
          </div>

          {/* Connection status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium
                           ${isConnected
                             ? 'bg-emerald/10 text-emerald'
                             : 'bg-red-500/10 text-red-400'
                           }`}>
            {isConnected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="p-2 rounded-lg bg-white/5 text-white/60 hover:bg-white/10 
                       hover:text-white transition-all"
            title="Refresh memories"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={onDeleteAll}
            className="p-2 rounded-lg bg-white/5 text-red-400 hover:bg-red-500/20 
                       transition-all"
            title="Delete all memories"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats bento row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="glass-panel rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-4 h-4 text-emerald" />
            <span className="text-xs text-white/50 uppercase tracking-wider">Memories</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {stats.total_memories.toLocaleString()}
          </div>
        </div>

        <div className="glass-panel rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-cyber-lime" />
            <span className="text-xs text-white/50 uppercase tracking-wider">Clients</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {stats.unique_clients}
          </div>
        </div>

        <div className="glass-panel rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-emerald" />
            <span className="text-xs text-white/50 uppercase tracking-wider">Model</span>
          </div>
          <div className="text-sm font-medium text-white truncate">
            all-MiniLM-L6-v2
          </div>
          <div className="text-xs text-white/40">384 dims</div>
        </div>

        <div className="glass-panel rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-emerald" />
            <span className="text-xs text-white/50 uppercase tracking-wider">Latest</span>
          </div>
          <div className="text-xs text-white/70 truncate">
            {stats.newest_memory
              ? new Date(stats.newest_memory).toLocaleDateString()
              : 'N/A'
            }
          </div>
        </div>
      </div>

      {/* Main bento grid */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100%-180px)]">
        {/* Left panel - Navigation */}
        <div className="col-span-3 glass-panel rounded-xl p-4 flex flex-col">
          <nav className="space-y-2">
            <button
              onClick={() => setActiveTab('all')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all
                         ${activeTab === 'all'
                           ? 'bg-emerald/10 text-emerald'
                           : 'text-white/60 hover:bg-white/5 hover:text-white'
                         }`}
            >
              <Database className="w-4 h-4" />
              <span>All Memories</span>
            </button>

            <button
              onClick={() => setActiveTab('search')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all
                         ${activeTab === 'search'
                           ? 'bg-emerald/10 text-emerald'
                           : 'text-white/60 hover:bg-white/5 hover:text-white'
                         }`}
            >
              <Search className="w-4 h-4" />
              <span>Search</span>
            </button>

            <button
              onClick={() => setActiveTab('add')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all
                         ${activeTab === 'add'
                           ? 'bg-emerald/10 text-emerald'
                           : 'text-white/60 hover:bg-white/5 hover:text-white'
                         }`}
            >
              <Plus className="w-4 h-4" />
              <span>Add Memory</span>
            </button>
          </nav>

          {/* Quick stats */}
          <div className="mt-auto pt-4 border-t border-white/10">
            <div className="text-xs text-white/40 mb-2">Storage</div>
            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald to-cyber-lime transition-all duration-500"
                style={{ width: `${Math.min(stats.total_memories / 100 * 100, 100)}%` }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-xs text-white/30">{stats.total_memories} items</span>
              <span className="text-xs text-white/30">longbow</span>
            </div>
          </div>
        </div>

        {/* Right panel - Content */}
        <div className="col-span-9 glass-panel rounded-xl p-4 overflow-hidden">
          {activeTab === 'all' && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">All Memories</h2>
                <span className="text-xs text-white/40">
                  {memories.length} shown
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3">
                {memories.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-white/30">
                    <Database className="w-12 h-12 mb-4 opacity-50" />
                    <span className="text-sm">No memories stored yet</span>
                    <span className="text-xs mt-1">Use the Add Memory tab to get started</span>
                  </div>
                ) : (
                  memories.map(memory => (
                    <MemoryCard key={memory.id} memory={memory} />
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'search' && (
            <SearchPanel
              onSearch={onSearch}
              results={searchResults}
              isSearching={isSearching}
            />
          )}

          {activeTab === 'add' && (
            <AddMemoryForm onAdd={onAdd} />
          )}
        </div>
      </div>
    </div>
  );
}

export default MemoryHUD;
