/**
 * MarketPage — market statistics with rarity breakdown per collection.
 *
 * Shows: liquidity score, floor prices by tier, rarity premiums,
 * price trend, sales velocity, and "rare at floor" warnings.
 */

import { useEffect, useState } from "react";
import { fetchMarketStats } from "../api/client";

const TIER_LABEL = {
  ultra_rare: "Ultra Rare",
  rare: "Rare",
  uncommon: "Uncommon",
  common: "Common",
};

const TIER_COLOR = {
  ultra_rare: "text-purple-400",
  rare:       "text-yellow-400",
  uncommon:   "text-blue-400",
  common:     "text-gray-400",
};

const TIER_BG = {
  ultra_rare: "bg-purple-500/10 border-purple-500/30",
  rare:       "bg-yellow-500/10 border-yellow-500/30",
  uncommon:   "bg-blue-500/10 border-blue-500/30",
  common:     "bg-gray-800 border-gray-700",
};

export default function MarketPage() {
  const [stats, setStats]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [sortBy, setSortBy]   = useState("liquidity");
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchMarketStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const sorted = [...stats].sort((a, b) => {
    if (sortBy === "liquidity") return b.liquidity_score - a.liquidity_score;
    if (sortBy === "floor")     return (a.floor_price ?? 999999) - (b.floor_price ?? 999999);
    if (sortBy === "sales")     return b.sales_7d - a.sales_7d;
    return 0;
  });

  return (
    <div className="p-4 pb-24">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-bold">Market</h1>
        <span className="text-xs text-gray-500">{stats.length} collections</span>
      </div>

      {/* Sort tabs */}
      <div className="flex gap-2 mb-4">
        {[
          { key: "liquidity", label: "Liquidity" },
          { key: "sales",     label: "Sales 7d" },
          { key: "floor",     label: "Floor" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setSortBy(t.key)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              sortBy === t.key
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <Skeleton />}
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!loading && !error && sorted.length === 0 && (
        <p className="text-gray-600 text-sm text-center mt-16">
          No data yet — wait for the first scan.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {sorted.map((item) => (
          <CollectionCard
            key={item.slug}
            item={item}
            isExpanded={expanded === item.slug}
            onToggle={() =>
              setExpanded(expanded === item.slug ? null : item.slug)
            }
          />
        ))}
      </div>
    </div>
  );
}

/* ── Collection card ───────────────────────────────────────────────────────── */

function CollectionCard({ item, isExpanded, onToggle }) {
  const hasRareAtFloor = detectRareAtFloor(item);
  const commonFloor = item.rarity_breakdown?.common?.floor_price;

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden">
      {/* Main row */}
      <button
        className="w-full text-left p-3 active:bg-gray-800 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between gap-2">
          {/* Left: name + badges */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-sm truncate">{item.name}</span>
              {hasRareAtFloor && (
                <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded-full font-medium">
                  RARE @ FLOOR
                </span>
              )}
              <TrendBadge trend={item.price_trend_7d} />
            </div>

            {/* Liquidity bar */}
            <div className="flex items-center gap-2 mt-1.5">
              <LiquidityBar score={item.liquidity_score} />
              <span className="text-[10px] text-gray-500">
                {item.sales_7d} sales/7d · {item.active_listings} listed
              </span>
            </div>
          </div>

          {/* Right: floor price */}
          <div className="text-right flex-shrink-0">
            {commonFloor != null ? (
              <>
                <p className="font-bold text-sm tabular-nums text-green-400">
                  {formatPrice(commonFloor)}
                  <span className="text-[11px] text-gray-400 ml-0.5">TON</span>
                </p>
                <p className="text-[10px] text-gray-500">floor</p>
              </>
            ) : (
              <p className="text-xs text-gray-600">—</p>
            )}
          </div>
        </div>
      </button>

      {/* Expanded: rarity breakdown */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-800 pt-3">
          <RarityBreakdown item={item} />
        </div>
      )}
    </div>
  );
}

/* ── Rarity breakdown table ────────────────────────────────────────────────── */

function RarityBreakdown({ item }) {
  const breakdown = item.rarity_breakdown || {};
  const tiers = ["ultra_rare", "rare", "uncommon", "common"].filter(
    (t) => breakdown[t]
  );

  if (tiers.length === 0) {
    return <p className="text-xs text-gray-600">No tier data yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
        Rarity Breakdown
      </h3>

      {tiers.map((tier) => {
        const td = breakdown[tier];
        return (
          <div
            key={tier}
            className={`rounded-lg border px-3 py-2 ${TIER_BG[tier]}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className={`text-xs font-semibold ${TIER_COLOR[tier]}`}>
                  {TIER_LABEL[tier]}
                </span>
                {td.premium_vs_common != null && tier !== "common" && (
                  <span className="text-[10px] text-gray-500">
                    {td.premium_vs_common.toFixed(1)}×
                  </span>
                )}
              </div>
              <div className="text-right">
                {td.floor_price != null ? (
                  <span className="text-sm font-bold tabular-nums">
                    {formatPrice(td.floor_price)}
                    <span className="text-[11px] text-gray-400 ml-0.5">TON</span>
                  </span>
                ) : (
                  <span className="text-xs text-gray-600">no listings</span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between mt-1">
              <span className="text-[10px] text-gray-500">
                {td.active_listings} listed
                {td.sales_30d > 0 && ` · ${td.sales_30d} sold/30d`}
              </span>
              {td.median_sale_price_30d != null && (
                <span className="text-[10px] text-gray-500">
                  median {formatPrice(td.median_sale_price_30d)} TON
                </span>
              )}
            </div>
          </div>
        );
      })}

      {/* Summary row */}
      <div className="flex items-center justify-between text-[10px] text-gray-500 px-1 pt-1">
        <span>
          {item.days_of_inventory != null
            ? `~${item.days_of_inventory.toFixed(0)} days inventory`
            : "no sales data"}
        </span>
        {item.last_sale_days_ago != null && (
          <span>last sale {item.last_sale_days_ago}d ago</span>
        )}
      </div>
    </div>
  );
}

/* ── Small UI components ───────────────────────────────────────────────────── */

function LiquidityBar({ score }) {
  const filled = Math.round(Math.min(score, 1) * 5);
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={`w-2.5 h-1.5 rounded-sm ${
            i < filled ? "bg-blue-500" : "bg-gray-700"
          }`}
        />
      ))}
    </div>
  );
}

function TrendBadge({ trend }) {
  if (!trend || trend === "unknown") return null;
  const cfg = {
    up:     { icon: "↑", cls: "text-green-400 bg-green-500/10" },
    down:   { icon: "↓", cls: "text-red-400 bg-red-500/10" },
    stable: { icon: "→", cls: "text-gray-400 bg-gray-800" },
  };
  const c = cfg[trend];
  if (!c) return null;
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${c.cls}`}>
      {c.icon}
    </span>
  );
}

/* ── Helpers ───────────────────────────────────────────────────────────────── */

/**
 * Detect if any rare/ultra_rare listing is priced at ≤130% of common floor.
 * (Frontend-side approximation — exact alerts come via Telegram.)
 */
function detectRareAtFloor(item) {
  const breakdown = item.rarity_breakdown || {};
  const commonFloor = breakdown.common?.floor_price;
  if (!commonFloor) return false;

  for (const tier of ["rare", "ultra_rare"]) {
    const td = breakdown[tier];
    if (!td?.floor_price) continue;
    // If rare floor is within 40% of common floor — flag it
    if (td.floor_price <= commonFloor * 1.4) return true;
  }
  return false;
}

function formatPrice(price) {
  if (price == null) return "—";
  const num = Number(price);
  return num >= 1000
    ? num.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : num.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="bg-gray-900 rounded-xl p-3 h-[72px] animate-pulse" />
      ))}
    </div>
  );
}
