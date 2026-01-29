import { useState } from 'react';
import { Plus, Loader2, Tag, X } from 'lucide-react';

interface AddMemoryFormProps {
  onAdd: (content: string, metadata: Record<string, unknown>) => void;
}

export function AddMemoryForm({ onAdd }: AddMemoryFormProps) {
  const [content, setContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState('');
  const [category, setCategory] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setIsSubmitting(true);

    const metadata: Record<string, unknown> = {};
    if (tags.length > 0) metadata.tags = tags;
    if (category) metadata.category = category;

    onAdd(content.trim(), metadata);

    // Reset form
    setContent('');
    setTags([]);
    setCategory('');
    setIsSubmitting(false);
  };

  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-emerald/10 flex items-center justify-center">
          <Plus className="w-4 h-4 text-emerald" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Add Memory</h2>
          <p className="text-xs text-white/40">Store new memories with embeddings</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
        {/* Content textarea */}
        <div className="mb-4">
          <label className="block text-xs text-white/50 mb-2">Content</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Enter memory content..."
            rows={6}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl 
                       text-white placeholder-white/30 outline-none resize-none
                       focus:border-emerald/50 focus:ring-1 focus:ring-emerald/30
                       transition-all"
          />
          <div className="flex justify-between mt-1">
            <span className="text-xs text-white/30">
              {content.length} characters
            </span>
          </div>
        </div>

        {/* Category */}
        <div className="mb-4">
          <label className="block text-xs text-white/50 mb-2">Category (optional)</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g., notes, tasks, ideas"
            className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg 
                       text-white placeholder-white/30 outline-none text-sm
                       focus:border-emerald/50 focus:ring-1 focus:ring-emerald/30
                       transition-all"
          />
        </div>

        {/* Tags */}
        <div className="mb-4">
          <label className="block text-xs text-white/50 mb-2">Tags</label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addTag();
                }
              }}
              placeholder="Add tag..."
              className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg 
                         text-white placeholder-white/30 outline-none text-sm
                         focus:border-emerald/50 transition-all"
            />
            <button
              type="button"
              onClick={addTag}
              disabled={!newTag.trim()}
              className="px-3 py-2 rounded-lg bg-white/5 text-white/60 hover:bg-white/10 
                         hover:text-white disabled:opacity-30 transition-all"
            >
              <Tag className="w-4 h-4" />
            </button>
          </div>

          {/* Tag list */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {tags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md 
                             bg-emerald/10 text-emerald text-xs"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    className="hover:text-emerald/70"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Submit button */}
        <div className="mt-auto">
          <button
            type="submit"
            disabled={!content.trim() || isSubmitting}
            className="w-full py-3 px-4 rounded-xl bg-emerald text-obsidian font-medium
                       hover:bg-emerald/90 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Storing...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                Store Memory
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default AddMemoryForm;
