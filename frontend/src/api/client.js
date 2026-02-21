const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

/**
 * Fetch gifts with multi-marketplace prices.
 * @param {Object} params - Query parameters
 * @param {string} [params.sort_by] - Sort field: 'name', 'best_price', 'spread_pct'
 * @param {string} [params.sort_order] - Sort direction: 'asc', 'desc'
 * @param {number} [params.min_spread_pct] - Minimum spread percentage filter
 * @param {string} [params.search] - Search query
 * @returns {Promise<{gifts: Array, meta: Object}>}
 */
export function fetchGifts(params = {}) {
  const searchParams = new URLSearchParams();

  if (params.sort_by) searchParams.set("sort_by", params.sort_by);
  if (params.sort_order) searchParams.set("sort_order", params.sort_order);
  if (params.min_spread_pct != null) searchParams.set("min_spread_pct", params.min_spread_pct);
  if (params.search) searchParams.set("search", params.search);

  const query = searchParams.toString();
  return request(`/gifts${query ? `?${query}` : ""}`);
}

/**
 * Fetch a single gift by slug.
 * @param {string} slug - Gift slug
 * @returns {Promise<Object>}
 */
export function fetchGift(slug) {
  return request(`/gifts/${slug}`);
}

export function fetchDeal(dealId) {
  return request(`/deals/${dealId}`);
}

export function createDeal(body) {
  return request("/deals/create", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Fetch market stats, optionally filtered by gift slug.
 * @param {string} [slug] - Optional gift slug to filter results
 * @returns {Promise<Array>} Array of market stats objects
 */
export function fetchMarketStats(slug) {
  return request(`/stats/market${slug ? `?slug=${slug}` : ""}`);
}
