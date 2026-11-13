// "Built by NOBS Agent" footer badge — same markup and inline styling as the
// snippet in the NOBS brand kit (built-by-badge.html). The kit embeds the
// logo as a data URI so it works on third-party sites under strict content
// policies; on this site the same mark is just served from /nobs-agent-mark.svg.
//
// NOTE: this is the NOBS Agent studio mark (brass hexagon). It belongs only
// inside this badge — the NOBS AI product logo is /logo-mark.png (purple).
export function BuiltByBadge() {
  return (
    <a
      href="https://www.nobs-agent.site"
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 14px",
        borderRadius: 999,
        background: "#0b0d12",
        textDecoration: "none",
        fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",
        fontSize: 13,
        lineHeight: 1,
      }}
    >
      <img src="/nobs-agent-mark.svg" alt="" width={16} height={16} style={{ display: "block" }} />
      <span style={{ color: "#8b93a3" }}>Built by</span>
      <span style={{ color: "#e4b343", fontWeight: 600 }}>NOBS Agent</span>
    </a>
  );
}
