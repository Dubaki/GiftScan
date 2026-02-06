/**
 * GiftDetailModal — bottom sheet with full price breakdown for a gift.
 */

import SpreadBadge from "./SpreadBadge";

export default function GiftDetailModal({ gift, onClose }) {
  if (!gift) return null;

  const hasPrices = gift.prices?.some((p) => p.price != null);
  const sortedPrices = [...(gift.prices || [])]
    .filter((p) => p.price != null)
    .sort((a, b) => Number(a.price) - Number(b.price));

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Sheet */}
      <div
        className="relative w-full max-w-lg bg-gray-900 rounded-t-2xl p-5 pb-8 animate-slide-up max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle */}
        <div className="flex justify-center mb-4">
          <div className="w-10 h-1 rounded-full bg-gray-700" />
        </div>

        {/* Header */}
        <div className="flex items-center gap-4 mb-5">
          <img
            src={gift.image_url}
            alt={gift.name}
            className="w-16 h-16 rounded-xl object-cover bg-gray-800"
          />
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold truncate">{gift.name}</h2>
            <p className="text-xs text-gray-500">
              {gift.slug} {gift.total_supply && `\u00b7 ${gift.total_supply.toLocaleString()} supply`}
            </p>
          </div>
          {gift.spread_pct != null && <SpreadBadge spreadPct={gift.spread_pct} />}
        </div>

        {/* Best / Worst summary */}
        {gift.best_price && gift.worst_price && (
          <div className="grid grid-cols-2 gap-3 mb-5">
            <PriceBox label="Best price" data={gift.best_price} color="text-green-400" />
            <PriceBox label="Worst price" data={gift.worst_price} color="text-red-400" />
          </div>
        )}

        {/* Spread row */}
        {gift.spread_ton != null && (
          <div className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 mb-5 text-sm">
            <span className="text-gray-400">Spread</span>
            <span className="tabular-nums font-medium">
              {formatPrice(gift.spread_ton)} TON
              {gift.spread_pct != null && (
                <span className="text-gray-500 ml-1">({gift.spread_pct}%)</span>
              )}
            </span>
          </div>
        )}

        {/* Price table */}
        {hasPrices ? (
          <div>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Prices by marketplace
            </h3>
            <div className="flex flex-col gap-1.5">
              {sortedPrices.map((p) => (
                <div
                  key={p.source}
                  className="flex items-center justify-between bg-gray-800/60 rounded-lg px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <SourceDot source={p.source} isBest={p.source === gift.best_price?.source} />
                    <span className="text-sm">{p.source}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-semibold tabular-nums ${
                      p.source === gift.best_price?.source ? "text-green-400" : ""
                    }`}>
                      {formatPrice(p.price)}
                    </span>
                    <span className="text-[11px] text-gray-500 ml-1">{p.currency || "TON"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-600 text-center">No price data available</p>
        )}

        {/* Close button */}
        <button
          onClick={onClose}
          className="mt-5 w-full py-2.5 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm font-medium transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function PriceBox({ label, data, color }) {
  return (
    <div className="bg-gray-800 rounded-lg px-3 py-2">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-0.5">{label}</p>
      <p className={`text-base font-bold tabular-nums ${color}`}>
        {formatPrice(data.price)}
        <span className="text-xs text-gray-400 ml-1">{data.currency || "TON"}</span>
      </p>
      <p className="text-[10px] text-gray-500">{data.source}</p>
    </div>
  );
}

function SourceDot({ source, isBest }) {
  return (
    <span
      className={`w-2 h-2 rounded-full ${isBest ? "bg-green-400" : "bg-gray-600"}`}
    />
  );
}

function formatPrice(price) {
  if (price == null) return "\u2014";
  const num = Number(price);
  if (num >= 1000) {
    return num.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
