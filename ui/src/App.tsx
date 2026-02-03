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
    graphData,
    searchMemories,
    addMemory,
    deleteAllMemories,
    refreshMemories,
    traverseGraph,
    addEdge,
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
          graphData={graphData}
          onSearch={searchMemories}
          onAdd={addMemory}
          onDeleteAll={deleteAllMemories}
          onRefresh={refreshMemories}
          onTraverse={traverseGraph}
          onAddEdge={addEdge}
        />
      </div>
    </div>
  );
}

export default App;
