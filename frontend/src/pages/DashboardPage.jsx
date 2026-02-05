import { useEffect, useState } from "react";
import { fetchGifts } from "../api/client";
import GiftCard from "../components/GiftCard";

export default function DashboardPage() {
  const [gifts, setGifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchGifts()
      .then(setGifts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = gifts.filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-4 pb-20">
      {/* Header */}
      <h1 className="text-xl font-bold">Scanner</h1>
      <p className="text-gray-400 text-xs mb-3">
        Fragment floor prices &middot; {gifts.length} gifts
      </p>

      {/* Search */}
      <input
        type="text"
        placeholder="Search gifts..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-gray-900 rounded-lg px-3 py-2 text-sm placeholder-gray-600 outline-none focus:ring-1 focus:ring-blue-500 mb-3"
      />

      {/* List */}
      {loading && <Skeleton />}
      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex flex-col gap-2">
        {filtered.map((gift) => (
          <GiftCard key={gift.slug} gift={gift} />
        ))}
      </div>

      {!loading && filtered.length === 0 && (
        <p className="text-gray-600 text-sm text-center mt-10">No gifts found.</p>
      )}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-gray-900 rounded-xl p-3 h-[60px] animate-pulse" />
      ))}
    </div>
  );
}
