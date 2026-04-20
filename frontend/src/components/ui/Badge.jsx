export default function Badge({ children, tone = "default", className = "" }) {
  const classes = ["ui-badge", `ui-badge--${tone}`, className].filter(Boolean).join(" ");
  return <span className={classes}>{children}</span>;
}
