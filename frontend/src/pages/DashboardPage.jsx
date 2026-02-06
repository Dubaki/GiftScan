import { useEffect, useState, useCallback } from "react";
import { fetchGifts } from "../api/client";
import GiftCard from "../components/GiftCard";
import FilterBar from "../components/FilterBar";
import GiftDetailModal from "../components/GiftDetailModal";

export default function DashboardPage() {
  const [data, setData] = useState({ gifts: [], meta: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  // Filter/sort state
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState("asc");
  const [minSpread, setMinSpread] = useState(null);
  const [selectedGift, setSelectedGift] = useState(null);

  const loadGifts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchGifts({
        sort_by: sortBy,
        sort_order: sortOrder,
        min_spread_pct: minSpread,
        search: search || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortOrder, minSpread, search]);

  useEffect(() => {
    loadGifts();
  }, [loadGifts]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (search !== "") {
        loadGifts();
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleSortChange = (newSortBy, newSortOrder) => {
    setSortBy(newSortBy);
    setSortOrder(newSortOrder);
  };

  const handleGiftClick = (gift) => {
    setSelectedGift(gift);
  };

  // Count arbitrage signals
  const arbitrageCount = data.gifts.filter((g) => g.arbitrage_signal).length;

  return (
    <div className="p-4 pb-20">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-bold">Scanner</h1>
        {arbitrageCount > 0 && (
          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
            {arbitrageCount} arbitrage
          </span>
        )}
      </div>

      <p className="text-gray-400 text-xs mb-3">
        {data.meta?.sources?.length || 1} source{data.meta?.sources?.length !== 1 ? "s" : ""} &middot;{" "}
        {data.meta?.total || data.gifts.length} gifts
        {data.meta?.scan_timestamp && (
          <> &middot; {formatTimeAgo(data.meta.scan_timestamp)}</>
        )}
      </p>

      {/* Search */}
      <input
        type="text"
        placeholder="Search gifts..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-gray-900 rounded-lg px-3 py-2 text-sm placeholder-gray-600 outline-none focus:ring-1 focus:ring-blue-500 mb-3"
      />

      {/* Filter Bar */}
      <FilterBar
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
        minSpread={minSpread}
        onMinSpreadChange={setMinSpread}
      />

      {/* List */}
      {loading && <Skeleton />}
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!loading && !error && (
        <div className="flex flex-col gap-2">
          {data.gifts.map((gift) => (
            <GiftCard key={gift.slug} gift={gift} onClick={handleGiftClick} />
          ))}
        </div>
      )}

      {!loading && !error && data.gifts.length === 0 && (
        <p className="text-gray-600 text-sm text-center mt-10">No gifts found.</p>
      )}

      {selectedGift && (
        <GiftDetailModal gift={selectedGift} onClose={() => setSelectedGift(null)} />
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

/**
 * Format timestamp as "X ago" string.
 */
function formatTimeAgo(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  return date.toLocaleDateString();
}
