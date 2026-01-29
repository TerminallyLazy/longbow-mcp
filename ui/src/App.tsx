import { useMemoryBridge } from './hooks/useMemoryBridge';
import ThreeBackground from './components/ThreeBackground';
import MemoryHUD from './components/MemoryHUD';

function App() {
  const {
    isConnected,
    stats,
    memories,
    searchResults,
    isSearching,
    searchMemories,
    addMemory,
    deleteAllMemories,
    refreshMemories
  } = useMemoryBridge();

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* Three.js Raymarching Background */}
      <ThreeBackground memoryCount={stats.total_memories} />

      {/* Main HUD */}
      <div className="relative z-10 w-full h-full">
        <MemoryHUD
          isConnected={isConnected}
          stats={stats}
          memories={memories}
          searchResults={searchResults}
          isSearching={isSearching}
          onSearch={searchMemories}
          onAdd={addMemory}
          onDeleteAll={deleteAllMemories}
          onRefresh={refreshMemories}
        />
      </div>
    </div>
  );
}

export default App;
