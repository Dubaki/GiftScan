/**
 * FilterBar — sorting and filtering controls for gift list.
 */

export default function FilterBar({
  sortBy,
  sortOrder,
  onSortChange,
  minSpread,
  onMinSpreadChange,
}) {
  const handleSortByChange = (e) => {
    onSortChange(e.target.value, sortOrder);
  };

  const handleSortOrderToggle = () => {
    onSortChange(sortBy, sortOrder === "asc" ? "desc" : "asc");
  };

  return (
    <div className="flex items-center gap-2 mb-3">
      {/* Sort dropdown */}
      <select
        value={sortBy}
        onChange={handleSortByChange}
        className="flex-1 bg-gray-900 text-sm rounded-lg px-2 py-1.5 border border-gray-800 outline-none focus:border-blue-500"
      >
        <option value="name">By Name</option>
        <option value="best_price">By Price</option>
        <option value="spread_pct">By Spread</option>
      </select>

      {/* Sort order toggle */}
      <button
        onClick={handleSortOrderToggle}
        className="p-1.5 bg-gray-900 rounded-lg border border-gray-800 hover:bg-gray-800 transition-colors"
        title={sortOrder === "asc" ? "Ascending" : "Descending"}
      >
        <SortIcon ascending={sortOrder === "asc"} />
      </button>

      {/* Min spread filter */}
      <div className="flex items-center gap-1">
        <span className="text-xs text-gray-500">Min:</span>
        <select
          value={minSpread ?? ""}
          onChange={(e) =>
            onMinSpreadChange(e.target.value ? Number(e.target.value) : null)
          }
          className="bg-gray-900 text-sm rounded-lg px-2 py-1.5 border border-gray-800 outline-none focus:border-blue-500"
        >
          <option value="">All</option>
          <option value="5">5%+</option>
          <option value="10">10%+</option>
          <option value="20">20%+</option>
        </select>
      </div>
    </div>
  );
}

function SortIcon({ ascending }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      className="w-5 h-5"
    >
      {ascending ? (
        <path d="M12 5v14M5 12l7-7 7 7" />
      ) : (
        <path d="M12 19V5M5 12l7 7 7-7" />
      )}
    </svg>
  );
}
