/**
 * GiftCard — per UI_WIREFRAMES.md section 2.
 *
 * Shows: icon, name, floor price, supply.
 * Green highlight when spread/profit > 10 % (placeholder — needs buy+sell to calc).
 */

export default function GiftCard({ gift }) {
  const hasPrice = gift.floor_price != null;

  return (
    <div className="flex items-center gap-3 bg-gray-900 rounded-xl p-3 active:bg-gray-800 transition-colors">
      {/* Thumbnail */}
      <img
        src={gift.image_url}
        alt={gift.name}
        className="w-12 h-12 rounded-lg object-cover bg-gray-800 flex-shrink-0"
        loading="lazy"
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm truncate">{gift.name}</p>
        {gift.total_supply && (
          <p className="text-[11px] text-gray-500">
            Supply: {gift.total_supply.toLocaleString()}
          </p>
        )}
      </div>

      {/* Price */}
      <div className="text-right flex-shrink-0">
        {hasPrice ? (
          <>
            <p className="font-bold text-sm tabular-nums">
              {Number(gift.floor_price).toLocaleString()}
              <span className="text-[11px] text-gray-400 ml-0.5">
                {gift.currency}
              </span>
            </p>
            <p className="text-[11px] text-gray-500">floor</p>
          </>
        ) : (
          <p className="text-xs text-gray-600">—</p>
        )}
      </div>
    </div>
  );
}
