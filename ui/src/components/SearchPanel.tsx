import { useState, useRef } from 'react';
import { Search, Loader2, Sparkles } from 'lucide-react';
import { SearchResult } from '../hooks/useMemoryBridge';
import MemoryCard from './MemoryCard';

interface SearchPanelProps {
  onSearch: (query: string, topK?: number) => void;
  results: SearchResult[];
  isSearching: boolean;
}

export function SearchPanel({ onSearch, results, isSearching }: SearchPanelProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), 10);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-emerald/10 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-emerald" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Semantic Search</h2>
          <p className="text-xs text-white/40">Find memories by meaning, not keywords</p>
        </div>
      </div>

      {/* Search form */}
      <form onSubmit={handleSubmit} className="relative mb-4">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search your memories..."
          className="w-full px-4 py-3 pl-12 bg-white/5 border border-white/10 rounded-xl 
                     text-white placeholder-white/30 outline-none
                     focus:border-emerald/50 focus:ring-1 focus:ring-emerald/30
                     transition-all"
        />
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />

        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 
                     px-3 py-1.5 rounded-lg bg-emerald/20 text-emerald text-xs font-medium
                     hover:bg-emerald/30 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        >
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            'Search'
          )}
        </button>
      </form>

      {/* Results */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {isSearching && results.length === 0 && (
          <div className="flex items-center justify-center h-32 text-white/40">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            <span className="text-sm">Searching memories...</span>
          </div>
        )}

        {!isSearching && results.length === 0 && query && (
          <div className="flex flex-col items-center justify-center h-32 text-white/40">
            <Search className="w-8 h-8 mb-2 opacity-50" />
            <span className="text-sm">No memories found</span>
            <span className="text-xs mt-1">Try a different query</span>
          </div>
        )}

        {!query && !isSearching && (
          <div className="flex flex-col items-center justify-center h-32 text-white/30">
            <Sparkles className="w-8 h-8 mb-2 opacity-50" />
            <span className="text-sm">Enter a search query</span>
            <span className="text-xs mt-1">Memories are matched by semantic similarity</span>
          </div>
        )}

        {results.map((result) => (
          <MemoryCard
            key={result.memory.id}
            memory={result.memory}
            score={result.score}
          />
        ))}
      </div>

      {/* Results count */}
      {results.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/10 text-center">
          <span className="text-xs text-white/40">
            Found {results.length} result{results.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}
    </div>
  );
}

export default SearchPanel;
