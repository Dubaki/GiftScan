import { NavLink } from "react-router-dom";

const tabs = [
  { to: "/", label: "Scanner", icon: ScannerIcon },
  { to: "/escrow", label: "Escrow", icon: EscrowIcon },
  { to: "/profile", label: "Profile", icon: ProfileIcon },
];

export default function TabBar() {
  return (
    <nav className="fixed bottom-0 inset-x-0 bg-gray-900 border-t border-gray-800 pb-[env(safe-area-inset-bottom)]">
      <div className="flex justify-around items-center h-14">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.to === "/"}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 text-xs transition-colors ${
                isActive ? "text-blue-400" : "text-gray-500"
              }`
            }
          >
            <t.icon />
            <span>{t.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

/* ── Inline SVG icons (24×24) ── */

function ScannerIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} className="w-6 h-6">
      <path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M8 12h8M12 8v8" />
    </svg>
  );
}

function EscrowIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} className="w-6 h-6">
      <path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} className="w-6 h-6">
      <circle cx={12} cy={8} r={4} />
      <path d="M20 21a8 8 0 1 0-16 0" />
    </svg>
  );
}
