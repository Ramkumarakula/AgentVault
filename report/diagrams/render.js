// Builds the report diagrams as SVG and renders them to PNG with headless Chrome/Edge.
//   node report/diagrams/render.js
// Output: report/diagrams/*.svg and *.png
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const OUT = __dirname;
const FONT = "Segoe UI, Arial, sans-serif";
const C = {
  blue: ["#E8EEFB", "#5B7BD5"],
  green: ["#E6F4EA", "#3C9A5F"],
  orange: ["#FDEEDC", "#E08A3C"],
  red: ["#FDE4E3", "#D0463F"],
  grey: ["#F3F4F6", "#8A8F98"],
  purple: ["#F1EAFB", "#8A63D2"],
};
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function box(x, y, w, h, color, lines, opt = {}) {
  const [fill, stroke] = C[color];
  const r = opt.r ?? 10;
  let s = `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${opt.sw ?? 1.6}"${opt.dash ? ' stroke-dasharray="6 4"' : ""}/>`;
  const lh = opt.lh ?? 17;
  const n = lines.length;
  const y0 = opt.top ? y + 22 : y + h / 2 - ((n - 1) * lh) / 2 + 5;
  lines.forEach((ln, i) => {
    const bold = i === 0 && !opt.noBold;
    const size = bold ? opt.titleSize ?? 14.5 : opt.size ?? 12;
    const mono = typeof ln === "object" && ln.mono;
    const text = typeof ln === "object" ? ln.t : ln;
    s += `<text x="${opt.left ? x + 14 : x + w / 2}" y="${y0 + i * lh}" text-anchor="${opt.left ? "start" : "middle"}" font-family="${mono ? "Consolas, monospace" : FONT}" font-size="${size}" font-weight="${bold ? 700 : 400}" fill="${bold ? "#1F2A44" : "#3B4252"}">${esc(text)}</text>`;
  });
  return s;
}

function arrow(points, opt = {}) {
  const d = points.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
  const col = opt.color ?? "#4B5563";
  return `<path d="${d}" fill="none" stroke="${col}" stroke-width="${opt.sw ?? 1.6}"${opt.dash ? ' stroke-dasharray="6 4"' : ""} marker-end="url(#ah${opt.red ? "r" : ""})"/>`;
}

function label(x, y, text, opt = {}) {
  const size = opt.size ?? 11.5;
  const w = text.length * size * (opt.mono ? 0.56 : 0.52) + 10;
  const anchor = opt.anchor ?? "middle";
  const rx = anchor === "middle" ? x - w / 2 : anchor === "start" ? x - 5 : x - w + 5;
  return `${opt.nobg ? "" : `<rect x="${rx}" y="${y - size}" width="${w}" height="${size + 6}" fill="#ffffff" opacity="0.92"/>`}<text x="${x}" y="${y}" text-anchor="${anchor}" font-family="${opt.mono ? "Consolas, monospace" : FONT}" font-size="${size}" font-style="${opt.italic ? "italic" : "normal"}" font-weight="${opt.bold ? 700 : 400}" fill="${opt.color ?? "#374151"}">${esc(text)}</text>`;
}

function svg(w, h, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
<defs>
<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4B5563"/></marker>
<marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#D0463F"/></marker>
</defs>
<rect width="${w}" height="${h}" fill="#ffffff"/>
${body}
</svg>`;
}

// ---------------------------------------------------------------- Figure: architecture
function architecture() {
  let b = "";
  b += box(40, 24, 270, 78, "green", ["Human owner", "MetaMask account (Ownable owner)", "sets policy, approves, can pause"]);
  b += box(365, 24, 270, 78, "purple", ["AI agent", "separate hot key (AGENT_PRIVATE_KEY)", "calls pay() on its own"]);
  b += box(690, 24, 270, 78, "grey", ["Funder (anyone)", "approve() then deposit()"]);

  b += `<rect x="20" y="150" width="960" height="420" rx="14" fill="#FFFBF5" stroke="#E08A3C" stroke-width="1.4" stroke-dasharray="7 5"/>`;
  b += label(36, 556, "Ethereum Sepolia testnet (chainId 11155111)  /  local Hardhat network for tests", { anchor: "start", bold: true, color: "#B45F1E", nobg: true, size: 12.5 });

  // Vault
  b += `<rect x="50" y="190" width="560" height="330" rx="12" fill="#F5F8FF" stroke="#5B7BD5" stroke-width="1.8"/>`;
  b += label(330, 214, "AgentVault.sol", { bold: true, size: 15, nobg: true, color: "#1F2A44" });
  b += box(70, 230, 255, 118, "blue", ["policies[agent]", "active, expiry", "perTxLimit, dailyLimit", "approvalThreshold", "spentInWindow, windowStart"], { lh: 16, size: 11.5 });
  b += box(335, 230, 255, 118, "blue", ["isPayeeAllowed", "agent => payee => bool", "", "per-agent allowlist", "set only by owner"], { lh: 16, size: 11.5 });
  b += box(70, 358, 520, 74, "blue", ["requests[]  (on-chain audit log)", "agent, to, amount, status (Pending | Executed | Rejected), createdAt, memo"], { lh: 18, size: 11.5 });
  b += box(70, 442, 520, 62, "grey", ["Inherited / library code (OpenZeppelin 5.4.0)", "Ownable  -  Pausable  -  ReentrancyGuard  -  SafeERC20"], { lh: 18, size: 11.5 });

  // token + payee
  b += box(700, 210, 250, 96, "orange", ["MockUSDC.sol", "ERC-20, 6 decimals", "TEST TOKEN, NO VALUE"]);
  b += box(700, 420, 250, 80, "green", ["Allowlisted payee", "e.g. an API or GPU service"]);

  // arrows
  b += arrow([[175, 102], [175, 190]]);
  b += label(175, 140, "policy / approve / pause", { size: 11 });
  b += arrow([[500, 102], [500, 190]]);
  b += label(500, 140, "pay(to, amount, memo)", { size: 11, mono: true });
  b += arrow([[825, 102], [825, 132], [600, 132], [600, 190]]);
  b += label(735, 126, "deposit(amount)", { size: 11, mono: true });
  b += arrow([[610, 258], [700, 258]]);
  b += label(655, 250, "safeTransfer", { size: 10.5, mono: true });
  b += arrow([[825, 306], [825, 420]]);
  b += label(825, 368, "balance moves", { size: 11 });
  return svg(1000, 590, b);
}

// ---------------------------------------------------------------- Figure: pay() flowchart
function payFlow() {
  let b = "";
  const cx = 280, w = 380, h = 46, gap = 26;
  const rows = [
    ["start", "Agent calls pay(to, amount, memo)"],
    ["q", "Vault paused?", "yes", "EnforcedPause"],
    ["q", "memo <= 140 bytes and amount > 0?", "no", "MemoTooLong / ZeroAmount"],
    ["q", "Agent active and not expired?", "no", "AgentNotActive / AgentExpired"],
    ["q", "Payee on this agent's allowlist?", "no", "PayeeNotAllowed"],
    ["q", "amount <= perTxLimit?", "no", "ExceedsPerTxLimit"],
    ["pend", "amount > approvalThreshold?", "yes", "Store as Pending, emit PaymentRequested, transfer nothing (owner decides later)"],
    ["step", "Roll fixed 24h window if now >= windowStart + 1 day"],
    ["q", "spentInWindow + amount <= dailyLimit?", "no", "ExceedsDailyLimit"],
    ["q", "Vault token balance >= amount?", "no", "InsufficientVaultBalance"],
    ["end", "spentInWindow += amount; store Executed; emit PaymentExecuted; safeTransfer(to, amount)"],
  ];
  let y = 20;
  rows.forEach((r, i) => {
    const [kind, text, br, out] = r;
    const x = cx - w / 2;
    if (kind === "start") b += box(x, y, w, h, "purple", [text], { r: 23 });
    else if (kind === "end") b += box(x, y, w, h + 26, "green", ["Execute", "spentInWindow += amount; store Executed", "emit PaymentExecuted; safeTransfer(to, amount)"], { titleSize: 13, size: 11.5, lh: 17 });
    else if (kind === "step") b += box(x, y, w, h, "blue", [text], { noBold: true, size: 12.5 });
    else b += box(x, y, w, h, "grey", [text], { noBold: true, size: 12.5, r: 4 });
    if (br) {
      const col = kind === "pend" ? "orange" : "red";
      const ox = 560, ow = 300;
      const parts = out.length > 40 ? [out.slice(0, out.indexOf(",") + 1), out.slice(out.indexOf(",") + 2)] : [out];
      if (kind === "pend") b += box(ox, y - 6, ow, h + 12, col, ["Pending (needs human)", "store request, emit PaymentRequested", "no tokens move"], { lh: 15, size: 11, titleSize: 12.5 });
      else b += box(ox, y + 4, ow, h - 8, col, ["revert " + parts[0]], { noBold: true, size: 12 });
      b += arrow([[cx + w / 2, y + h / 2], [ox, y + h / 2]], { red: kind !== "pend" });
      b += label((cx + w / 2 + ox) / 2, y + h / 2 - 5, br, { size: 11, bold: true, color: kind === "pend" ? "#B45F1E" : "#B42318" });
    }
    if (i < rows.length - 1) {
      b += arrow([[cx, y + h], [cx, y + h + gap]]);
      const nxt = rows[i + 1];
      if (r[0] === "q" || r[0] === "pend") {
        const okWord = r[2] === "yes" ? "no" : "yes";
        b += label(cx + 18, y + h + 17, okWord, { size: 11, bold: true, anchor: "start", color: "#2F7A4A", nobg: true });
      }
      void nxt;
    }
    y += h + gap;
  });
  return svg(890, y + 30, b);
}

// ---------------------------------------------------------------- Figure: approval sequence
function sequence() {
  let b = "";
  const cols = [
    ["AI agent", "purple", 110],
    ["AgentVault", "blue", 380],
    ["Human owner", "green", 650],
    ["MockUSDC", "orange", 890],
  ];
  cols.forEach(([n, c, x]) => {
    b += box(x - 85, 16, 170, 44, c, [n]);
  });
  const X = Object.fromEntries(cols.map(([n, , x]) => [n, x]));
  let y = 95;
  const msg = (from, to, text, opt = {}) => {
    const a = X[from], c = X[to];
    b += arrow([[a, y], [c + (c > a ? -2 : 2), y]], { dash: opt.dash });
    b += label((a + c) / 2, y - 7, text, { size: 11.2, mono: opt.mono });
    y += opt.step ?? 46;
  };
  const note = (who, text, color, h = 40, w = 300) => {
    const x = X[who];
    b += box(x - w / 2, y - 18, w, h, color, text, { noBold: true, size: 11, lh: 15 });
    y += h + 14;
  };
  msg("AI agent", "AgentVault", "pay(payee, 80 mUSDC, \"GPU rental\")", { mono: true });
  note("AgentVault", ["checks pass, 80 > threshold 50", "store request #1 as Pending, move nothing"], "orange");
  msg("AgentVault", "AI agent", "returns requestId = 1", { dash: true });
  msg("AgentVault", "Human owner", "event PaymentRequested(1, agent, payee, 80, memo)", { dash: true });
  note("Human owner", ["reviews amount, payee and memo", "(off-chain, e.g. in Etherscan / a script)"], "green");
  msg("Human owner", "AgentVault", "approveRequest(1)", { mono: true });
  note("AgentVault", ["re-check: active, not expired, payee allowed,", "amount <= perTx, fits window, balance ok"], "blue", 40, 320);
  msg("AgentVault", "MockUSDC", "safeTransfer(payee, 80 mUSDC)", { mono: true });
  msg("AgentVault", "Human owner", "events PaymentApproved, PaymentExecuted", { dash: true });
  const life = cols.map(([, , x]) => `<line x1="${x}" y1="60" x2="${x}" y2="${y - 20}" stroke="#9CA3AF" stroke-width="1.2" stroke-dasharray="5 4"/>`).join("");
  return svg(1000, y, life + b);
}

// ---------------------------------------------------------------- Figure: request states
function states() {
  let b = "";
  b += `<circle cx="60" cy="170" r="11" fill="#1F2A44"/>`;
  b += box(150, 140, 190, 60, "purple", ["pay() accepted", "all policy checks passed"], { lh: 16, size: 11.5 });
  b += arrow([[71, 170], [150, 170]]);
  b += box(470, 40, 200, 64, "green", ["Executed", "tokens transferred"], { lh: 18 });
  b += box(470, 230, 200, 64, "orange", ["Pending", "nothing transferred"], { lh: 18 });
  b += box(770, 330, 190, 60, "grey", ["Rejected", "final, nothing moved"], { lh: 18 });
  b += arrow([[340, 160], [405, 160], [405, 72], [470, 72]]);
  b += label(405, 118, "amount <= threshold", { size: 11 });
  b += arrow([[340, 180], [405, 180], [405, 262], [470, 262]]);
  b += label(405, 226, "amount > threshold", { size: 11 });
  b += arrow([[620, 230], [620, 104]]);
  b += label(632, 160, "approveRequest(id)", { size: 11, mono: true, anchor: "start", nobg: true });
  b += label(632, 176, "policy re-checked", { size: 10.5, italic: true, nobg: true, anchor: "start" });
  b += arrow([[670, 262], [865, 262], [865, 330]]);
  b += label(770, 256, "rejectRequest(id)", { size: 11, mono: true });
  // self loop
  b += `<path d="M520,294 C520,350 450,350 450,300 C450,296 455,294 470,288" fill="none" stroke="#D0463F" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#ahr)"/>`;
  b += label(470, 372, "approve reverts if a re-check fails:", { size: 10.5, color: "#B42318", nobg: true });
  b += label(470, 387, "request stays Pending", { size: 10.5, color: "#B42318", nobg: true });
  b += label(820, 72, "Executed and Rejected are final:", { size: 10.5, italic: true, nobg: true });
  b += label(820, 87, "approve/reject again -> RequestNotPending", { size: 10.5, italic: true, nobg: true });
  return svg(1000, 410, b);
}

// ---------------------------------------------------------------- Figure: fixed window
function windowFig() {
  let b = "";
  const x0 = 70, x1 = 930, y = 200, hours = 36;
  const X = (h) => x0 + ((x1 - x0) * h) / hours;
  b += `<line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" stroke="#374151" stroke-width="1.5" marker-end="url(#ah)"/>`;
  for (let h = 0; h <= 36; h += 3) {
    b += `<line x1="${X(h)}" y1="${y}" x2="${X(h)}" y2="${y + 6}" stroke="#374151"/>`;
    b += label(X(h), y + 22, `${h}h`, { size: 11, nobg: true });
  }
  // windows
  b += `<rect x="${X(0)}" y="${y - 150}" width="${X(24) - X(0)}" height="150" fill="#E8EEFB" stroke="#5B7BD5" stroke-dasharray="5 4"/>`;
  b += label((X(0) + X(24)) / 2, y - 158, "window 1: [0h, 24h)", { size: 11.5, bold: true, nobg: true });
  b += `<rect x="${X(24.5)}" y="${y - 150}" width="${X(36) - X(24.5)}" height="150" fill="#E6F4EA" stroke="#3C9A5F" stroke-dasharray="5 4"/>`;
  b += label((X(24.5) + X(36)) / 2, y - 158, "window 2: starts at first payment >= 24h (24.5h)", { size: 11.5, bold: true, nobg: true });
  const bar = (h, amt, col, txt) => {
    const hh = (amt / 250) * 120;
    b += `<rect x="${X(h) - 9}" y="${y - hh}" width="18" height="${hh}" fill="${col}" rx="2"/>`;
    b += label(X(h), y - hh - 6, txt, { size: 10.5, nobg: true });
  };
  bar(3, 50, "#5B7BD5", "50");
  bar(20, 50, "#5B7BD5", "50");
  bar(23, 150, "#5B7BD5", "150");
  bar(24.5, 100, "#3C9A5F", "100");
  bar(26, 150, "#3C9A5F", "150");
  b += `<path d="M${X(23)},${y + 40} L${X(23)},${y + 32} L${X(26)},${y + 32} L${X(26)},${y + 40}" fill="none" stroke="#D0463F" stroke-width="1.5"/>`;
  b += label((X(23) + X(26)) / 2, y + 56, "500 mUSDC executed between 23h and 26h = 2 x dailyLimit (250)", { size: 11.5, color: "#B42318", bold: true, nobg: true });
  b += label(x0, 22, "dailyLimit = 250 mUSDC. Each window individually stays <= 250, but the boundary allows a burst.", { size: 12, anchor: "start", nobg: true });
  return svg(1000, 275, b);
}

const figs = {
  fig_architecture: architecture(),
  fig_pay_flowchart: payFlow(),
  fig_approval_sequence: sequence(),
  fig_request_states: states(),
  fig_fixed_window: windowFig(),
};

const browsers = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
];
const browser = browsers.find((p) => fs.existsSync(p));
for (const [name, s] of Object.entries(figs)) {
  const svgPath = path.join(OUT, `${name}.svg`);
  fs.writeFileSync(svgPath, s);
  const [, w, h] = s.match(/width="(\d+)" height="(\d+)"/).map(Number);
  const html = path.join(OUT, `${name}.html`);
  fs.writeFileSync(html, `<!doctype html><html><body style="margin:0;background:#fff">${s}</body></html>`);
  if (!browser) {
    console.log(`wrote ${name}.svg (no Chrome/Edge found for PNG)`);
    continue;
  }
  const png = path.join(OUT, `${name}.png`);
  execFileSync(browser, [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--force-device-scale-factor=2",
    `--window-size=${w},${h}`,
    `--screenshot=${png}`,
    "file:///" + html.replace(/\\/g, "/"),
  ], { stdio: "ignore" });
  fs.unlinkSync(html);
  console.log(`rendered ${name}.png (${w}x${h} @2x)`);
}
