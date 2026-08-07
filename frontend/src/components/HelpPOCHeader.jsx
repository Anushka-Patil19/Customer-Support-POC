import { NavLink } from "react-router-dom";
import "./HelpPOCHeader.css";

const PAGES = [
  { path: "/ttvdcat", label: "TTVDCAT", subtitle: "Detail Category Code Validation" },
  { path: "/tsadetc", label: "TSADETC", subtitle: "Detail Code Control Form - Student" },
  { path: "/tsadetl", label: "TSADETL", subtitle: "Student Account Detail" },
];

export default function HelpPOCHeader() {
  return (
    <header className="hp-topbar">
      <div className="hp-brand">HelpPOC</div>
      <nav className="hp-nav">
        {PAGES.map((p) => (
          <NavLink
            key={p.path}
            to={p.path}
            className={({ isActive }) => `hp-nav-link${isActive ? " hp-nav-link--active" : ""}`}
          >
            {p.label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

export function PageTitle({ code, subtitle }) {
  return (
    <div className="hp-page-title">
      {subtitle} <span className="hp-page-code">{code} 9.3 (POC)</span>
    </div>
  );
}
