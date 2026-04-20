const ICONS = {
  documents: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8 3.75h6.2L19.25 8.8V18A2.25 2.25 0 0 1 17 20.25H8A2.25 2.25 0 0 1 5.75 18V6A2.25 2.25 0 0 1 8 3.75Z" />
      <path d="M14 3.75V8a1 1 0 0 0 1 1h4.25" />
      <path d="M9 12.25h6" />
      <path d="M9 15.75h6" />
    </svg>
  ),
  summary: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4.75v14.5" />
      <path d="M4.75 12h14.5" />
      <path d="M6.75 6.75l3.1 3.1" />
      <path d="M14.15 14.15l3.1 3.1" />
    </svg>
  ),
  qa: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6.5 5.75h11A1.75 1.75 0 0 1 19.25 7.5v7A1.75 1.75 0 0 1 17.5 16.25H9l-4.25 3v-11A2.25 2.25 0 0 1 6.5 5.75Z" />
    </svg>
  ),
  quiz: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M9 4.75a7.25 7.25 0 1 0 0 14.5" />
      <path d="M15 4.75a7.25 7.25 0 1 1 0 14.5" />
      <path d="M9.75 9.5h.01" />
      <path d="M9.75 14.5h.01" />
      <path d="M14.25 9.5h.01" />
      <path d="M14.25 14.5h.01" />
    </svg>
  ),
  flashcards: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7.25 7.25h9.5a2 2 0 0 1 2 2v7.5a2 2 0 0 1-2 2h-9.5a2 2 0 0 1-2-2v-7.5a2 2 0 0 1 2-2Z" />
      <path d="M5.25 14V6.75a1.5 1.5 0 0 1 1.5-1.5H14" />
      <path d="M9 12h6" />
    </svg>
  ),
};

export default function SectionIcon({ name, className = "" }) {
  return <span className={`section-icon ${className}`.trim()}>{ICONS[name] || null}</span>;
}
