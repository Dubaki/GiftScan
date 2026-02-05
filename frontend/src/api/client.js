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

export function fetchGifts() {
  return request("/gifts");
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
