/**
 * SpreadBadge — shows spread percentage with color coding.
 *
 * Green (>= 10%): Strong arbitrage opportunity
 * Yellow (5-10%): Moderate opportunity
 * Gray (< 5%): Low/no opportunity
 */

export default function SpreadBadge({ spreadPct, className = "" }) {
  if (spreadPct == null) return null;

  let bgColor, textColor;

  if (spreadPct >= 10) {
    bgColor = "bg-green-500/20";
    textColor = "text-green-400";
  } else if (spreadPct >= 5) {
    bgColor = "bg-yellow-500/20";
    textColor = "text-yellow-400";
  } else {
    bgColor = "bg-gray-700/50";
    textColor = "text-gray-400";
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${bgColor} ${textColor} ${className}`}
    >
      {spreadPct.toFixed(1)}%
    </span>
  );
}
