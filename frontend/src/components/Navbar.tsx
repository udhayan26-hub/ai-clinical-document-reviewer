import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/analyze", label: "New Analysis", end: false },
  { to: "/analyses", label: "History", end: false },
];

export default function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <NavLink to="/" className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4.5 w-4.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3-15H8.25A2.25 2.25 0 006 4.5v15A2.25 2.25 0 008.25 21.75h7.5A2.25 2.25 0 0018 19.5v-15a2.25 2.25 0 00-2.25-2.25H15M9 3.75c0 .621.504 1.125 1.125 1.125h1.75c.621 0 1.125-.504 1.125-1.125M9 3.75c0-.621.504-1.125 1.125-1.125h1.75c.621 0 1.125.504 1.125 1.125" />
            </svg>
          </span>
          <span className="text-[15px] font-semibold text-slate-900">AI Clinical Document Reviewer</span>
        </NavLink>
        <nav className="flex items-center gap-1">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-sky-50 text-sky-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
