export default function BrandMark({ className = "" }) {
  return (
    <div className={className} aria-hidden="true">
      <svg viewBox="0 0 32 32" focusable="false">
        <rect x="1" y="1" width="30" height="30" rx="8" fill="#ea8d8c" />
        <rect x="8.3" y="9.2" width="7.2" height="11.2" rx="2.1" fill="none" stroke="#fff6f5" strokeWidth="1.9" />
        <rect x="16.5" y="9.2" width="7.2" height="11.2" rx="2.1" fill="none" stroke="#fff6f5" strokeWidth="1.9" />
        <line x1="16" y1="9.2" x2="16" y2="20.4" stroke="#fff6f5" strokeWidth="1.9" strokeLinecap="round" />
      </svg>
    </div>
  );
}
