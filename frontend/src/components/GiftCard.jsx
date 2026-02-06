/**
 * GiftCard — displays gift with multi-marketplace prices.
 *
 * Shows: thumbnail, name, best price with source badge, spread percentage.
 * Mini price list shows all available marketplace prices.
 */

import SpreadBadge from "./SpreadBadge";

export default function GiftCard({ gift, onClick }) {
  const hasPrices = gift.prices?.some((p) => p.price != null);
  const bestPrice = gift.best_price;

  return (
    <div
      className="flex items-center gap-3 bg-gray-900 rounded-xl p-3 active:bg-gray-800 transition-colors cursor-pointer"
      onClick={() => onClick?.(gift)}
    >
      {/* Thumbnail */}
      <img
        src={gift.image_url}
        alt={gift.name}
        className="w-12 h-12 rounded-lg object-cover bg-gray-800 flex-shrink-0"
        loading="lazy"
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className="font-semibold text-sm truncate">{gift.name}</p>
          {gift.arbitrage_signal && (
            <SpreadBadge spreadPct={gift.spread_pct} />
          )}
        </div>

        {/* Mini price list */}
        {hasPrices && (
          <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-0.5">
            {gift.prices
              .filter((p) => p.price != null)
              .map((p) => (
                <span
                  key={p.source}
                  className={`text-[10px] ${
                    p.source === bestPrice?.source
                      ? "text-green-400"
                      : "text-gray-500"
                  }`}
                >
                  {getSourceShort(p.source)}: {formatPrice(p.price)}
                </span>
              ))}
          </div>
        )}
      </div>

      {/* Best Price */}
      <div className="text-right flex-shrink-0">
        {bestPrice ? (
          <>
            <p className="font-bold text-sm tabular-nums text-green-400">
              {formatPrice(bestPrice.price)}
              <span className="text-[11px] text-gray-400 ml-0.5">
                {bestPrice.currency || "TON"}
              </span>
            </p>
            <p className="text-[10px] text-gray-500">
              {bestPrice.source}
            </p>
          </>
        ) : (
          <p className="text-xs text-gray-600">—</p>
        )}
      </div>
    </div>
  );
}

/**
 * Format price with thousand separators.
 */
function formatPrice(price) {
  if (price == null) return "—";
  const num = Number(price);
  if (num >= 1000) {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/**
 * Get short name for marketplace source.
 */
function getSourceShort(source) {
  const shorts = {
    Fragment: "Frag",
    GetGems: "GG",
    Tonnel: "Ton",
    MRKT: "MR",
    Portals: "Por",
  };
  return shorts[source] || source.slice(0, 3);
}
