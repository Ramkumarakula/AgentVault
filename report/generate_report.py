"""Generates report/AgentVault_Report.docx in the same layout as the course's earlier reports.

    python report/generate_report.py            # build the .docx
    powershell -File report/finalize_word.ps1   # (Windows + Word) update TOC/page numbers, export PDF

Every number in the report is read from a real output file in report/ (tests, coverage, Slither, gas, demo)
and code excerpts are cut from contracts/AgentVault.sol, so the report cannot drift from the code.
If deployments/sepolia.json and report/demo_output_sepolia.txt exist, the Sepolia sections are filled in;
otherwise clearly marked placeholders are inserted.
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "report"
DIA = REP / "diagrams"
OUT = REP / "AgentVault_Report.docx"
BLUE = RGBColor(0x1F, 0x38, 0x64)
TEXT_W = 9026  # dxa, A4 with 2.54 cm margins


def need(path: Path) -> str:
    if not path.exists():
        sys.exit(f"missing {path.relative_to(ROOT)} - run the tests/demo first (see README)")
    return path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ real data
test_out = need(REP / "test_output.txt")
cov_out = need(REP / "coverage_summary.txt")
slither_out = need(REP / "slither_output.txt")
gas_out = need(REP / "gas_report.txt")
demo_local = need(REP / "demo_output_local.txt").rstrip()
contract_src = need(ROOT / "contracts" / "AgentVault.sol")
mock_src = need(ROOT / "contracts" / "MockUSDC.sol")

m = re.search(r"(\d+) passing", test_out)
TESTS_PASSING = int(m.group(1))
TESTS_FAILING = int(re.search(r"(\d+) failing", test_out).group(1)) if "failing" in test_out else 0

# group counts from mocha output (indentation based)
groups, cur = {}, None
for line in test_out.splitlines():
    if not line.strip() or "passing" in line:
        continue
    if "✔" in line or re.match(r"\s+\d+\) ", line):
        groups[cur] = groups.get(cur, 0) + 1
    else:
        cur = line.strip()
assert sum(groups.values()) == TESTS_PASSING, (groups, TESTS_PASSING)

cov = {}
for line in cov_out.splitlines():
    cells = [c.strip() for c in line.split("|")]
    if len(cells) >= 5 and cells[0] in ("AgentVault.sol", "MockUSDC.sol", "All files"):
        cov[cells[0]] = cells[1:5]
assert "AgentVault.sol" in cov and "All files" in cov

SLITHER_N = int(re.search(r"(\d+) result\(s\) found", slither_out).group(1))
SLITHER_DET = int(re.search(r"with (\d+) detectors", slither_out).group(1))
slither_ts = len(re.findall(r"uses timestamp for comparisons", slither_out))
slither_ver = len(re.findall(r"necessitates a version too recent|is not recommended for deployment", slither_out))
assert slither_ts + slither_ver == SLITHER_N, (slither_ts, slither_ver, SLITHER_N)

gas_methods, gas_deploy = [], []
section = None
for line in gas_out.splitlines():
    if "Methods" in line and "Contracts" not in line:
        section = "m"
    if "Deployments" in line:
        section = "d"
    cells = [c.strip() for c in re.split(r"[|·│]", line) if c.strip()]
    if section == "m" and len(cells) >= 5 and re.match(r"^[a-zA-Z]+$", cells[0]) and cells[0] not in ("Min",):
        gas_methods.append(cells[:5])
    if section == "d" and len(cells) >= 4 and cells[0] in ("AgentVault", "MockUSDC"):
        gas_deploy.append(cells)
assert gas_methods and gas_deploy

dep_path = ROOT / "deployments" / "sepolia.json"
DEP = json.loads(dep_path.read_text()) if dep_path.exists() else None
demo_sep_path = REP / "demo_output_sepolia.txt"
DEMO_SEP = demo_sep_path.read_text(encoding="utf-8").rstrip() if demo_sep_path.exists() else None


def extract_function(src: str, signature: str) -> str:
    i = src.index(signature)
    start = src.rfind("\n", 0, i) + 1
    depth, j, seen = 0, src.index("{", i), False
    while True:
        ch = src[j]
        if ch == "{":
            depth += 1
            seen = True
        elif ch == "}":
            depth -= 1
            if seen and depth == 0:
                break
        j += 1
    lines = src[start : j + 1].splitlines()
    ind = min(len(l) - len(l.lstrip()) for l in lines if l.strip())
    return "\n".join(l[ind:] for l in lines)


# ------------------------------------------------------------------ document + styles
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.54))
sec.different_first_page_header_footer = True

core = doc.core_properties
core.title = "AgentVault: An On-Chain Spending-Policy Wallet for AI Agents"
core.author = "Ramkumar (RK)"
core.subject = "Smart Contract and Development - course project report"

# document defaults: Times New Roman 12
styles_el = doc.styles.element
rpr_default = styles_el.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
for tag in ("w:rFonts", "w:sz", "w:szCs"):
    el = rpr_default.find(qn(tag))
    if el is not None:
        rpr_default.remove(el)
rf = OxmlElement("w:rFonts")
for a in ("ascii", "hAnsi", "eastAsia", "cs"):
    rf.set(qn(f"w:{a}"), "Times New Roman")
rpr_default.append(rf)
for tag in ("w:sz", "w:szCs"):
    el = OxmlElement(tag)
    el.set(qn("w:val"), "24")
    rpr_default.append(el)


def style_font(style, size=None, bold=None, italic=None, color=None, caps=None, font="Times New Roman"):
    f = style.font
    f.name = font
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    for k in list(rfonts.attrib):
        if "Theme" in k:
            del rfonts.attrib[k]
    for a in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{a}"), font)
    if size:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    f.color.rgb = color if color else RGBColor(0, 0, 0)
    if caps is not None:
        f.all_caps = caps


normal = doc.styles["Normal"]
style_font(normal, 12)
normal.paragraph_format.space_after = Pt(0)

h1 = doc.styles["Heading 1"]
style_font(h1, 16, bold=True, color=BLUE, caps=True)
h1.paragraph_format.space_before = Pt(0)
h1.paragraph_format.space_after = Pt(12)
h1.paragraph_format.keep_with_next = True
h1.paragraph_format.page_break_before = True

h2 = doc.styles["Heading 2"]
style_font(h2, 14, bold=True, color=BLUE)
h2.paragraph_format.space_before = Pt(14)
h2.paragraph_format.space_after = Pt(6)
h2.paragraph_format.keep_with_next = True

h3 = doc.styles["Heading 3"]
style_font(h3, 12, bold=True)
h3.paragraph_format.space_before = Pt(10)
h3.paragraph_format.space_after = Pt(5)
h3.paragraph_format.keep_with_next = True

cap = doc.styles["Caption"]
style_font(cap, 10, bold=False, italic=True)
cap.paragraph_format.space_before = Pt(3)
cap.paragraph_format.space_after = Pt(10)
cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER

for name in ("List Bullet", "List Number"):
    style_font(doc.styles[name], 12)


# ------------------------------------------------------------------ helpers
INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|\*[^*]+?\*)")


def add_inline(p, text, size=None):
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        elif part.startswith("`"):
            r = p.add_run(part[1:-1])
            r.font.name = "Consolas"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt((size or 12) - 1.5)
        elif part.startswith("*"):
            r = p.add_run(part[1:-1])
            r.italic = True
        else:
            r = p.add_run(part)
        if size and not part.startswith("`"):
            r.font.size = Pt(size)
    return p


def para(text, after=8, align="both", keep_next=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.line_spacing = 1.5
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align == "both" else WD_ALIGN_PARAGRAPH.LEFT
    pf.keep_with_next = keep_next
    return add_inline(p, text)


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = Pt(17)
        add_inline(p, it)
    doc.paragraphs[-1].paragraph_format.space_after = Pt(10)


def numbered(items):
    for i, it in enumerate(items, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.9)
        pf.first_line_indent = Cm(-0.6)
        pf.space_after = Pt(4)
        pf.line_spacing = Pt(17)
        pf.tab_stops.add_tab_stop(Cm(0.9))
        add_inline(p, f"{i}.\t{it}")
    doc.paragraphs[-1].paragraph_format.space_after = Pt(10)


def heading(text, level):
    return doc.add_heading(text, level)


FIGS, TABS = [], []


def caption(kind, text):
    lst = FIGS if kind == "Figure" else TABS
    lst.append(text)
    p = doc.add_paragraph(f"{kind} {len(lst)}: {text}", style="Caption")
    if kind == "Table":
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
    return len(lst)


def figure(png, text, width_cm=15.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(str(png), width=Cm(width_cm))
    return caption("Figure", text)


def next_fig():
    return len(FIGS) + 1


def next_tab():
    return len(TABS) + 1


def shade(cell, fill):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def table(title, header, rows, widths, size=10, code_cols=()):
    caption("Table", title)
    total = sum(widths)
    widths = [round(w * TEXT_W / total) for w in widths]
    t = doc.add_table(rows=1, cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblpr = t._element.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "999999")
        borders.append(e)
    tblpr.append(borders)
    mar = OxmlElement("w:tblCellMar")
    for edge, v in (("top", 50), ("left", 100), ("bottom", 50), ("right", 100)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.append(mar)
    grid = t._element.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))

    def fill_row(cells, values, head=False):
        for ci, (c, v) in enumerate(zip(cells, values)):
            c.width = Emu_dxa(widths[ci])
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = Pt(13)
            p.paragraph_format.space_after = Pt(0)
            if head:
                r = p.add_run(v)
                r.bold = True
                r.font.size = Pt(size + 0.5)
                shade(c, "D9E2F3")
            elif ci in code_cols:
                r = p.add_run(v)
                r.font.name = "Consolas"
                r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
                r.font.size = Pt(size - 1)
            else:
                add_inline(p, v, size)

    fill_row(t.rows[0].cells, header, head=True)
    trpr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    trpr.append(th)
    for row in rows:
        cells = t.add_row().cells
        fill_row(cells, row)
    for row in t.rows:
        cant = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)
    return t


def Emu_dxa(dxa):
    return Cm(dxa / 567.0)


def code(text, size=8.5, keep=True):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.35)
    pf.right_indent = Cm(0.35)
    pf.space_before = Pt(6)
    pf.space_after = Pt(10)
    pf.line_spacing = 1.0
    pf.keep_together = keep
    ppr = p._element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    ppr.append(shd)
    limit = int(431 / (0.55 * size)) - 2  # characters per line at this font size

    def wrap(line):
        out = []
        ind = len(line) - len(line.lstrip())
        cont = " " * (ind + 8)
        while len(line) > limit:
            cut = line.rfind(", ", 0, limit)
            if cut > ind + 8:
                head, rest = line[: cut + 1], line[cut + 2 :]
            else:
                cut = line.rfind(" ", 0, limit)
                if cut <= ind + 8:
                    cut = limit
                head, rest = line[:cut], line[cut:]
            out.append(head.rstrip())
            line = cont + rest.lstrip()
        out.append(line)
        return out

    lines = [w for raw in text.split("\n") for w in wrap(raw)]
    for i, line in enumerate(lines):
        r = p.add_run(line)
        r.font.name = "Consolas"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(size)
        if i < len(lines) - 1:
            r.add_break()
    return p


SHOTS = []


def placeholder(text, height_cm=4.0):
    SHOTS.append(text)
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    c.width = Cm(14)
    tcpr = c._element.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "dashed")
        e.set(qn("w:sz"), "8")
        e.set(qn("w:color"), "808080")
        b.append(e)
    tcpr.append(b)
    shade(c, "FAFAFA")
    trpr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:trHeight")
    h.set(qn("w:val"), str(int(height_cm * 567)))
    h.set(qn("w:hRule"), "atLeast")
    trpr.append(h)
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    tcpr.append(vAlign)
    p = c.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"[Insert screenshot: {text}]")
    r.italic = True
    r.font.size = Pt(11)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(2)


def todo(text):
    """Inline, clearly marked placeholder for data that does not exist yet."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"[TO BE FILLED AFTER SEPOLIA DEPLOYMENT: {text}]")
    r.bold = True
    r.font.highlight_color = 7  # yellow
    return p


def centered_title(text, before=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(14)
    return p


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def field(paragraph, instr, placeholder_text=""):
    def fc(t):
        r = OxmlElement("w:r")
        f = OxmlElement("w:fldChar")
        f.set(qn("w:fldCharType"), t)
        r.append(f)
        return r

    paragraph._p.append(fc("begin"))
    r = OxmlElement("w:r")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r.append(it)
    paragraph._p.append(r)
    paragraph._p.append(fc("separate"))
    if placeholder_text:
        paragraph.add_run(placeholder_text)
    paragraph._p.append(fc("end"))


# footer: centred page number from page 2 (page 1 has an empty first-page footer)
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
field(fp, "PAGE", "2")
for r in fp.runs:
    r.font.size = Pt(10)
sec.first_page_footer.paragraphs[0].text = ""
sec.first_page_header.paragraphs[0].text = ""

# ================================================================== PAGE 1: completely blank
blank = doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()
blank.add_run().add_break(WD_BREAK.PAGE)

# ================================================================== INDEX
centered_title("INDEX")
toc_p = doc.add_paragraph()
field(toc_p, 'TOC \\o "1-2" \\h \\z \\u', "Right-click and choose Update Field to build the index.")
page_break()

# ================================================================== LISTS (filled at the end)
centered_title("LIST OF FIGURES")
figs_marker = doc.add_paragraph()
centered_title("LIST OF TABLES", before=18)
tabs_marker = doc.add_paragraph()

# ================================================================== ABSTRACT
heading("Abstract", 1)
para(
    "AI agents are starting to pay for services on their own, for example through the x402 protocol, which "
    "uses the HTTP 402 \"Payment Required\" status code for machine-to-machine payments [8], [9]. Wallet "
    "products for agents appeared in 2026 [9], [11]. The open question is control. If the only limit on an "
    "agent's spending is its prompt or the program around it, a prompt injection or a leaked key can empty "
    "the wallet. Security guidance for agentic wallets therefore recommends spending caps, recipient "
    "allowlists, expiry and human approval above a threshold, enforced by the wallet or contract and not by "
    "the model [11]."
)
para(
    "This project, **AgentVault**, is a small Solidity implementation of that idea on Ethereum. A human owner "
    "funds a vault with an ERC-20 token and registers an agent address with a policy: a per-payment limit, a "
    "limit per fixed 24-hour window, an approval threshold, an expiry time and a list of allowed payees. The "
    "agent calls `pay()`. Payments inside the policy and at or below the threshold are executed at once. "
    "Payments above the threshold are stored as *Pending* and move no tokens until the owner calls "
    "`approveRequest()`, which checks the policy again at that moment. Anything outside the policy reverts "
    "with a custom error. The contracts use OpenZeppelin Contracts 5.4.0 (Ownable, Pausable, "
    "ReentrancyGuard, SafeERC20) and a 6-decimal test token, MockUSDC, which has no value."
)
a = cov["AgentVault.sol"]
para(
    f"The Hardhat test suite has {TESTS_PASSING} tests, all passing, including a malicious-token reentrancy "
    f"test and a seeded random test of 300 payments with time jumps. Coverage of AgentVault.sol is {a[0]} % of "
    f"statements, {a[1]} % of branches, {a[2]} % of functions and {a[3]} % of lines. Slither 0.9.3 reported "
    f"{SLITHER_N} informational or low findings and no high or medium ones. A scripted demo shows one "
    "payment executed, two payments rejected by the contract, and one payment held for human approval and "
    "then executed. The work is a course case study on a testnet. It has not been audited and is not intended "
    "for real funds."
)
p = para("**Keywords:** smart contracts, Solidity, ERC-20, AI agents, agent payments, spending policy, "
         "human-in-the-loop, x402, ERC-8004, account abstraction.")

# ================================================================== 1 INTRODUCTION
heading("1. Introduction", 1)
heading("1.1 Background", 2)
para(
    "A smart contract is a program stored on a blockchain whose code and state every node can check. The "
    "Ethereum white paper describes the goal as a blockchain with a built-in Turing-complete programming "
    "language in which anyone can write contracts with their own rules [1]. Solidity is the most common "
    "language for such contracts; its documentation describes it as an object-oriented, high-level language "
    "for implementing smart contracts [2]. Because the contract enforces its rules itself, the parties do not "
    "need to trust each other's servers."
)
para(
    "Software agents built on large language models can now call tools and APIs on their own. Some of those "
    "calls cost money. The x402 protocol lets a server answer a request with HTTP 402 and payment details; the "
    "agent pays from its wallet, sends proof, and gets the resource without a human in the loop [8]. In early "
    "2026 wallet providers released products aimed at agents: according to QuillAudits, Coinbase launched "
    "Agentic Wallets in February 2026 and MetaMask released its Agent Wallet [11]. On-chain measurements show "
    "that the rail is used, although most of the volume measured so far is not clearly agentic [10]."
)
heading("1.2 Motivation", 2)
para(
    "An agent that can pay is useful, but it is also an attractive target. QuillAudits lists prompt injection, "
    "over-broad session keys, compromised runtimes and unlimited token approvals as the main risks, and "
    "summarises the defence as \"never let the agent decide everything on its own\" [11]. The Spark article "
    "on agent wallet policy makes the same point from the architecture side: the policy engine replaces human "
    "judgement, so its quality sets the security boundary [9]. A limit that lives only in the agent's prompt "
    "is not a security boundary, because the prompt is the part an attacker can influence."
)
para(
    "This project moves the limits into a smart contract. The contract cannot be talked out of its rules: an "
    "agent that has been tricked, or a thief holding the agent's key, can at most spend what the policy "
    "allows, and only to addresses the owner approved."
)
heading("1.3 Organisation of the Report", 2)
para(
    "Chapter 2 covers the background (smart contracts, ERC-20, account abstraction, agent payments and "
    "ERC-8004). Chapters 3 and 4 state the problem and the objectives. Chapters 5 and 6 describe the "
    "architecture and the contract design. Chapter 7 covers the implementation, Chapter 8 the testing, and "
    "Chapter 9 the deployment on the Sepolia testnet. Chapter 10 analyses security, Chapter 11 lists "
    "limitations and future work, and Chapter 12 concludes. The appendices contain the setup steps and a "
    "selected code listing."
)

# ================================================================== 2 BACKGROUND
heading("2. Background", 1)
heading("2.1 Smart Contracts and Ethereum", 2)
para(
    "Ethereum keeps a global state made of accounts. An externally owned account (EOA) is controlled by a "
    "private key; a contract account is controlled by its code. A transaction signed by an EOA can call a "
    "contract function, which runs on every node and either changes state or reverts as a whole. Each "
    "operation costs gas, paid in ETH, which bounds the work a call can do [1]. Solidity code is compiled "
    "to EVM bytecode; the compiler version and its settings (optimizer, EVM version) decide the exact "
    "bytecode, which matters later when the source is verified on a block explorer [2]."
)
para(
    "Code on a public chain cannot be patched quietly, so mistakes are costly. Projects therefore build on "
    "reviewed libraries such as OpenZeppelin Contracts, described by its maintainers as \"a library for "
    "secure smart contract development\" [12], and check their code with tests and static analysers such as "
    "Slither [14]."
)
heading("2.2 ERC-20 Tokens", 2)
para(
    "ERC-20 defines a standard API for tokens inside smart contracts [3]: `balanceOf`, `transfer`, "
    "`approve`, `allowance` and `transferFrom`, plus `Transfer` and `Approval` events. A contract that "
    "wants to pull tokens from a user needs an allowance first (`approve`), and then calls `transferFrom`. "
    "Stablecoins such as USDC follow this interface, which is why agent payment systems settle mostly in "
    "ERC-20 stablecoins; TRM Labs found 99.6 % of the x402 settlement value they measured to be in USDC [10]. "
    "AgentVault uses a 6-decimal test token, MockUSDC, so that amounts look like USDC amounts without having "
    "any value. Some real tokens behave differently from the plain standard (fees on transfer, blocklists), "
    "so the vault uses OpenZeppelin's SafeERC20 wrapper, which reverts if a transfer fails [12]."
)
heading("2.3 Account Abstraction: ERC-4337 and EIP-7702", 2)
para(
    "Normally only EOAs can start transactions, and an EOA's rules are fixed: one key, full control. "
    "**ERC-4337** (status Final) brings account abstraction without changing the consensus layer [4]. Users "
    "sign a *UserOperation* that goes to a separate mempool; *bundlers* pack many of them into one transaction "
    "to a singleton *EntryPoint* contract, which validates and executes each one through the user's smart "
    "account. Optional *paymasters* can sponsor gas. Because validation is custom code, a smart account can "
    "enforce rules such as limited session keys."
)
para(
    "**EIP-7702** (status Final) adds a transaction type that lets an EOA set code for itself: the account "
    "signs an authorization, and a delegation indicator makes calls to the EOA run the code of a chosen "
    "contract [5]. The stated aims include batching, sponsorship and privilege de-escalation, i.e. sub-keys "
    "with narrower permissions [5]. Both standards are natural places to put an agent spending policy in a "
    "real wallet; AgentVault instead uses a plain vault contract, which is simpler to build and test in a "
    "course project (see Chapter 11)."
)
heading("2.4 AI Agent Payments and x402", 2)
para(
    "x402 builds on the HTTP 402 \"Payment Required\" status code for machine-to-machine micro-payments [8]. "
    "In the flow described by Chainlink, an agent requests a paid resource, receives a 402 response with an "
    "invoice (cost and destination), pays from a connected wallet, and repeats the request with proof of "
    "payment; the server verifies it and returns the resource [8]. The Spark article states that the protocol "
    "was originally published by Coinbase's Developer Platform under the Apache 2.0 licence and that the agent "
    "signs a stablecoin transfer authorization [9]."
)
para(
    "How much of this traffic is really agents is still small and hard to measure. TRM Labs identified about "
    "USD 52.7 million across 198.9 million settlement transactions through known x402 facilitators on Base, "
    "Solana and Polygon since May 2025. After removing self-payments and other non-commerce flows, about "
    "USD 25.62 million remained, and they bound the agent-driven share between 0.6 % and 7.5 %, because "
    "\"a scheduled script and an agent produce the same record\" [10]. The relevance for this project is not "
    "the volume but the pattern: software that holds a key and pays without asking."
)
heading("2.5 ERC-8004: Trustless Agents", 2)
para(
    "ERC-8004 (status Draft, created 2025-08-13) proposes three on-chain registries so that agents can be "
    "discovered and trusted across organisations without prior trust [6]. The **Identity Registry** gives "
    "each agent an ERC-721 based handle pointing to a registration file; the **Reputation Registry** stores "
    "feedback about agents; the **Validation Registry** records independent checks of an agent's work [6]. "
    "The reference contracts are published by the ERC-8004 team, and their README lists deployments on "
    "Ethereum mainnet and on Sepolia, while noting that the validation part is still being discussed [7]. "
    "ERC-8004 answers *who* an agent is and whether it is trusted; AgentVault answers a different question, "
    "*how much* a given agent may spend. The two could be combined (Chapter 11)."
)
heading("2.6 Existing Approaches to Agent Spending Control", 2)
para(
    "The sources describe several places where an agent's spending policy can be enforced. Table "
    f"{next_tab()} compares them with this project."
)
table(
    "Where an agent's spending policy can be enforced",
    ["Approach", "How the policy is enforced", "Notes from sources"],
    [
        ["In the agent's prompt or code only", "The agent is told its limits", "Not a security boundary: the agent is the part most likely to be manipulated [11]."],
        ["Off-chain policy server with MPC co-signing", "Policy server holds a key share and only co-signs allowed transactions", "Described as a 2-of-3 design (agent, policy server, human) [9]."],
        ["Smart-account session keys (ERC-4337 / ERC-7715)", "Smart wallet validation limits what a session key may do", "Recommended controls: scope, short expiry, fast revocation [9], [11]."],
        ["Contract vault with on-chain policy (this project)", "Vault contract checks limits, allowlist, expiry and approvals before any transfer", "Simple and fully testable; the owner key remains a single point of control (Chapter 10)."],
    ],
    [3, 3.4, 3.6],
)

# ================================================================== 3 PROBLEM STATEMENT
heading("3. Problem Statement", 1)
para(
    "An AI agent that pays for services needs a key that can move funds. Whoever controls that key, the "
    "intended agent, a manipulated agent or a thief, can spend everything the key controls. The problem this "
    "project addresses is:"
)
p = para(
    "*How can a human give an AI agent the ability to make payments on its own, while the limits on those "
    "payments are enforced by the blockchain itself, so that a misbehaving or compromised agent cannot "
    "exceed them, and large payments still need a human decision?*",
)
para("Concretely, the system must prevent the following:")
numbered([
    "**Overspending in one payment** - the agent sends more than a sensible amount in a single call.",
    "**Overspending over time** - many small payments add up to more than the owner intended per day.",
    "**Paying the wrong party** - the agent is tricked into paying an attacker's address.",
    "**Spending after it should have stopped** - the agent keeps spending after its task ended or after the "
    "owner withdrew its permission.",
    "**Large payments without a human** - payments above some amount happen without anyone looking at them.",
    "**Stale approvals** - the owner approves an old request although the situation has changed (agent "
    "revoked, payee removed).",
])
para(
    "All of these must hold even if the agent's prompt, code or key is fully under an attacker's control, "
    "which means they must be checked by the contract, not by the agent."
)

# ================================================================== 4 OBJECTIVES
heading("4. Objectives", 1)
heading("4.1 Objectives and Scope", 2)
bullets([
    "Design and implement a Solidity vault, **AgentVault**, in which an owner sets a per-agent policy "
    "(per-payment limit, 24-hour window limit, approval threshold, expiry, payee allowlist).",
    "Execute small payments immediately, hold large ones as Pending until the owner approves, and re-check the "
    "policy at approval time.",
    "Follow common security practice: checks-effects-interactions, `nonReentrant`, SafeERC20, custom errors, "
    "input validation, events for every state change, NatSpec comments.",
    "Test every rule with Hardhat, including time-dependent rules (window reset, expiry), a reentrancy attack "
    "and a property-style random test; measure coverage and run Slither.",
    "Provide a demo script that shows the policy from the agent's side, and deploy the contracts on the Sepolia "
    "testnet with verified source on Etherscan.",
    "Document the design, the threat model and the known limitations honestly.",
])
para(
    "Out of scope: a web front end, real stablecoins, mainnet deployment, integration with an actual "
    "LLM agent framework, and a professional audit. The \"agent\" in the demo is a script holding a separate key."
)
heading("4.2 Functional and Non-Functional Requirements", 2)
table(
    "Functional requirements",
    ["ID", "Requirement", "Implemented by"],
    [
        ["FR1", "Owner creates or updates an agent policy with validated limits and expiry.", "setAgentPolicy"],
        ["FR2", "Owner allows or removes payees per agent.", "setPayee"],
        ["FR3", "Anyone can fund the vault; only the owner can withdraw.", "deposit, withdraw"],
        ["FR4", "Agent pays an allowlisted payee within perTx and window limits; small payments execute at once.", "pay"],
        ["FR5", "Payments above the approval threshold are stored as Pending without moving tokens.", "pay"],
        ["FR6", "Owner approves (with policy re-check) or rejects a Pending request.", "approveRequest, rejectRequest"],
        ["FR7", "Owner can revoke an agent and pause all agent payments.", "revokeAgent, pause, unpause"],
        ["FR8", "Every payment and request is recorded on-chain and emitted as an event.", "requests[], events"],
    ],
    [1, 6, 3],
    code_cols=(2,),
)
para("The non-functional requirements are:")
bullets([
    "**Enforcement on-chain:** no rule may depend on the agent behaving correctly.",
    "**Safety of token movement:** checks-effects-interactions order, `nonReentrant`, SafeERC20.",
    "**Clarity of failure:** each rejected call reverts with a named custom error that carries the values "
    "involved, so a script or person can see why.",
    "**Reproducibility:** pinned tool versions and compiler settings identical in Hardhat, Remix and Etherscan.",
    "**No secrets in the repository:** keys only in a local, git-ignored `.env` file.",
])
heading("4.3 Hardware and Software Requirements", 2)
para(
    "The project was developed and tested on Windows 11 with Node.js 20.20.2. Any machine that runs Node.js "
    f"20 or later is enough; no special hardware is needed. Table {next_tab()} lists the software, with the "
    "versions pinned in `package.json`."
)
table(
    "Software requirements",
    ["Component", "Version or note"],
    [
        ["Solidity compiler", "0.8.28, optimizer enabled (200 runs), EVM version cancun"],
        ["Hardhat", "2.29.1 with @nomicfoundation/hardhat-toolbox 6.1.2 (ethers v6.16.0, chai 4.5.0, network helpers 1.1.2)"],
        ["OpenZeppelin Contracts", "5.4.0 (Ownable, Pausable, ReentrancyGuard, ERC20, SafeERC20)"],
        ["Coverage / static analysis", "solidity-coverage 0.8.17; Slither 0.9.3 (Python 3.11)"],
        ["Configuration", "dotenv 16.6.1, local `.env` file (git-ignored)"],
        ["Deployment", "Sepolia testnet; Remix IDE + MetaMask, or `scripts/deploy.js`"],
        ["Report", "python-docx; diagrams rendered from SVG with headless Chrome"],
    ],
    [3, 7],
)

# ================================================================== 5 ARCHITECTURE
heading("5. System Architecture", 1)
heading("5.1 Overview", 2)
para(
    f"Figure {next_fig()} shows the components. The **owner** is a human with a normal wallet (MetaMask). "
    "The **agent** is a separate key used by software; in this project it is the script `scripts/demo.js`. "
    "Both talk only to the **AgentVault** contract. The vault holds the tokens of one ERC-20 contract, "
    "**MockUSDC**, and moves them to **payees** only when the policy allows it. Anyone may fund the vault."
)
figure(DIA / "fig_architecture.png", "AgentVault architecture")
heading("5.2 Components", 2)
table(
    "Components of the system",
    ["Component", "Role"],
    [
        ["AgentVault.sol", "Holds the tokens. Stores one policy per agent, a payee allowlist per agent and every payment in `requests[]`. Inherits Ownable, Pausable and ReentrancyGuard and uses SafeERC20."],
        ["MockUSDC.sol", "ERC-20 test token with 6 decimals and an owner-only `mint`. Marked TEST TOKEN, NO VALUE."],
        ["scripts/deploy.js", "Deploys both contracts, writes `deployments/<network>.json`, optionally verifies on Etherscan. Refuses any chain other than Hardhat (31337) or Sepolia (11155111)."],
        ["scripts/demo.js", "Owner funds and configures the vault; the agent then tries four payments that show each rule."],
        ["test/AgentVault.test.js", f"{TESTS_PASSING} unit, property and attack tests."],
        ["flat/*.sol", "Flattened sources used for the Remix deployment and Etherscan single-file verification."],
    ],
    [3, 7],
)
heading("5.3 Actors and Permissions", 2)
table(
    "Who may call which function",
    ["Function", "Owner", "Agent", "Anyone"],
    [
        ["setAgentPolicy, revokeAgent, setPayee", "Yes", "No", "No"],
        ["pause, unpause, withdraw", "Yes", "No", "No"],
        ["approveRequest, rejectRequest", "Yes", "No", "No"],
        ["pay", "Only if also registered as an agent", "Yes (own policy)", "No (AgentNotActive)"],
        ["deposit", "Yes", "Yes", "Yes"],
        ["renounceOwnership", "Disabled (RenounceDisabled)", "No", "No"],
        ["views: policies, requests, isPayeeAllowed, remainingInWindow", "Yes", "Yes", "Yes"],
    ],
    [4.2, 2.6, 1.8, 1.8],
    code_cols=(0,),
)
para(
    "Unauthorised calls to owner functions revert with OpenZeppelin's `OwnableUnauthorizedAccount(caller)` "
    "error; the tests check this for every owner function (Chapter 8)."
)

# ================================================================== 6 CONTRACT DESIGN
heading("6. Smart Contract Design", 1)
heading("6.1 Data Structures", 2)
para(
    "The contract keeps three pieces of state besides the inherited owner and pause flag: a policy per agent, "
    f"an allowlist per agent, and an array of payment requests (Table {next_tab()}). Limits use `uint128` and "
    "timestamps `uint64` to keep the structs small; the `amount` argument is checked against `perTxLimit` "
    "(a `uint128`) before it is narrowed, so the cast cannot truncate."
)
table(
    "State variables and structs of AgentVault",
    ["Name", "Type", "Meaning"],
    [
        ["token", "IERC20 immutable", "The only token the vault holds and pays out; set in the constructor, zero address rejected."],
        ["policies", "mapping(address => AgentPolicy)", "Per agent: active, perTxLimit, dailyLimit, approvalThreshold, expiry, spentInWindow, windowStart."],
        ["isPayeeAllowed", "mapping(address => mapping(address => bool))", "agent => payee => allowed."],
        ["requests", "PaymentRequest[]", "agent, to, amount, status (Pending, Executed, Rejected), createdAt, memo. One entry per accepted pay() call."],
        ["WINDOW_DURATION", "constant uint256", "1 days (86 400 s)."],
        ["MAX_MEMO_LENGTH", "constant uint256", "140 bytes."],
    ],
    [2.3, 3.5, 5],
    code_cols=(0, 1),
)
code(extract_function(contract_src, "struct AgentPolicy {"), keep=True)
heading("6.2 Functions", 2)
table(
    "Public functions of AgentVault",
    ["Function", "Caller", "What it does"],
    [
        ["constructor(token)", "Deployer", "Stores the token; reverts ZeroAddress for address(0). Deployer becomes owner."],
        ["setAgentPolicy(agent, perTx, daily, threshold, expiry)", "Owner", "Validates and stores the policy, marks the agent active. Keeps current window usage when updating."],
        ["revokeAgent(agent)", "Owner", "Sets active = false; reverts AgentNotActive if already inactive."],
        ["setPayee(agent, payee, allowed)", "Owner", "Adds or removes a payee; rejects zero addresses and the vault itself."],
        ["deposit(amount)", "Anyone", "Pulls tokens with safeTransferFrom (needs prior approve)."],
        ["withdraw(to, amount)", "Owner", "Sends vault tokens out; works while paused."],
        ["pause() / unpause()", "Owner", "Emergency stop for pay and approveRequest."],
        ["pay(to, amount, memo)", "Agent", "Executes or stores as Pending according to the policy; returns the request id."],
        ["approveRequest(id)", "Owner", "Re-checks the policy and executes a Pending request."],
        ["rejectRequest(id)", "Owner", "Marks a Pending request Rejected; works while paused."],
        ["requestCount(), remainingInWindow(agent)", "Anyone", "Views used by scripts and the demo."],
    ],
    [4.2, 1.4, 5],
    code_cols=(0,),
)
heading("6.3 Policy Rules and Validation", 2)
para("`setAgentPolicy` accepts a policy only if:")
bullets([
    "`agent` is not the zero address;",
    "`0 < perTxLimit` and `approvalThreshold <= perTxLimit <= dailyLimit` (otherwise `InvalidLimits` with the three values);",
    "`expiry > block.timestamp` (otherwise `ExpiryNotInFuture`).",
])
para(
    "An agent is considered expired when `block.timestamp > expiry`, so a payment in the block whose timestamp "
    "equals `expiry` is still allowed; the tests check both sides of this boundary. When an existing policy "
    "is updated, `spentInWindow` and `windowStart` are kept, so that calling `setAgentPolicy` again cannot "
    "hand out a fresh daily allowance. If the owner lowers `dailyLimit` below the amount already spent, the "
    "remaining allowance is treated as zero instead of underflowing."
)
heading("6.4 Flow of pay()", 2)
para(
    f"Figure {next_fig()} shows the order of checks in `pay()`. The cheap checks come first. If the amount is "
    "above the approval threshold, the request is stored as Pending and nothing else happens: it is not "
    "counted against the window yet, because the owner may reject it. Otherwise the window is rolled if 24 "
    "hours have passed, the window limit and the vault balance are checked, the state is updated and only "
    "then are tokens transferred (checks-effects-interactions)."
)
figure(DIA / "fig_pay_flowchart.png", "Flowchart of pay() with the custom error for each rejected case", 14.5)
heading("6.5 Human-in-the-Loop Approval", 2)
para(
    f"Figure {next_fig()} follows a payment above the threshold. The agent's call returns a request id and "
    "emits `PaymentRequested`. The owner reviews it and calls `approveRequest(id)`. Because a request can be "
    "hours old, approval re-checks everything that might have changed: the agent must still be active and "
    "not expired, the payee must still be allowlisted, the amount must fit the *current* `perTxLimit` and the "
    "current window, and the vault must hold enough tokens. If any check fails, the approval reverts and the "
    "request stays Pending, so the owner can retry later or reject it."
)
figure(DIA / "fig_approval_sequence.png", "Sequence of a payment that needs human approval")
para(
    f"Figure {next_fig()} shows the possible states of a request. Executed and Rejected are final; trying to "
    "approve or reject them again reverts with `RequestNotPending`."
)
figure(DIA / "fig_request_states.png", "States of a payment request", 14.5)
heading("6.6 The Fixed 24-Hour Window", 2)
para(
    "The daily limit uses a **fixed** window, not a rolling one. The window starts when the policy is created. "
    "On the first execution at or after `windowStart + 1 day`, `windowStart` becomes that block's timestamp and "
    f"`spentInWindow` is reset to zero. Figure {next_fig()} shows the consequence: each window on its own never "
    "exceeds `dailyLimit`, but an agent can spend the full limit just before a window ends and again just "
    "after, i.e. up to twice the limit within a short time. A true rolling window would need a history of "
    "payments and more gas. The trade-off is accepted and documented, and the owner should choose "
    "`dailyLimit` with this in mind."
)
figure(DIA / "fig_fixed_window.png", "Fixed window: each window stays within the limit, the boundary allows a burst")
heading("6.7 Custom Errors and Events", 2)
table(
    "Custom errors raised by AgentVault",
    ["Error", "Raised when"],
    [
        ["ZeroAddress / ZeroAmount", "A required address or amount is zero."],
        ["InvalidLimits(threshold, perTx, daily)", "Limits violate 0 < perTx, threshold <= perTx <= daily."],
        ["ExpiryNotInFuture(expiry, now)", "Policy expiry is not in the future."],
        ["InvalidPayee(payee)", "Payee is zero or the vault itself."],
        ["AgentNotActive(agent) / AgentExpired(agent, expiry)", "Caller is not an active agent, or its expiry has passed."],
        ["PayeeNotAllowed(agent, payee)", "Payee is not on this agent's allowlist."],
        ["ExceedsPerTxLimit(amount, perTx)", "Single payment above the per-payment limit."],
        ["ExceedsDailyLimit(amount, remaining)", "Payment does not fit the current window."],
        ["MemoTooLong(length, max)", "Memo longer than 140 bytes."],
        ["InsufficientVaultBalance(available, required)", "Vault holds less than the amount."],
        ["RequestNotFound(id) / RequestNotPending(id, status)", "Approve or reject on a missing or finished request."],
        ["RenounceDisabled()", "Owner tries to renounce ownership."],
    ],
    [4.6, 5.4],
    code_cols=(0,),
)
para(
    "Events are emitted for every state change: `AgentPolicySet`, `AgentRevoked`, `PayeeSet`, `Deposited`, "
    "`Withdrawn`, `PaymentExecuted`, `PaymentRequested`, `PaymentApproved` and `PaymentRejected`. Agent, payee "
    "and request id are indexed so that an off-chain tool can follow one agent's activity."
)

# ================================================================== 7 IMPLEMENTATION
heading("7. Implementation", 1)
heading("7.1 Technology Stack", 2)
para(
    "The contracts are written in Solidity 0.8.28 and built with Hardhat 2.29.1. The compiler settings "
    "(optimizer on with 200 runs, EVM version cancun) are fixed in `hardhat.config.js` and must be the same in "
    "Remix and on Etherscan, otherwise the verified bytecode does not match. OpenZeppelin Contracts 5.4.0 "
    "provides access control, the pause switch, the reentrancy guard and SafeERC20 [12]. Scripts use ethers v6 "
    "through the Hardhat toolbox. Hardhat's main documentation site now covers Hardhat 3 [13]; this project "
    "deliberately stays on Hardhat 2, whose documentation notes that it is reaching end of life [13]."
)
heading("7.2 Key Code Excerpts", 2)
para(
    "The core of the contract is `pay()` (long lines are wrapped to fit the page). The order of the statements is the order of Figure "
    f"{FIGS.index('Flowchart of pay() with the custom error for each rejected case') + 1}: validation, the "
    "Pending branch, then effects (window, request record, event) and finally the token transfer."
)
code(extract_function(contract_src, "function pay("))
para(
    "The window logic is in one private helper, used by both `pay()` and `approveRequest()`, so the two paths "
    "cannot disagree:"
)
code(extract_function(contract_src, "function _consumeWindow("))
para("`approveRequest()` re-checks the policy before it changes anything:")
code(extract_function(contract_src, "function approveRequest("))
heading("7.3 Scripts and Configuration", 2)
table(
    "Scripts and configuration files",
    ["File", "Purpose"],
    [
        ["hardhat.config.js", "Compiler settings; reads SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY, AGENT_PRIVATE_KEY, ETHERSCAN_API_KEY from `.env`. Keys are accepted only if they look like 64 hex characters."],
        ["scripts/lib.js", "Shared helpers; refuses to run on any chain other than 31337 or 11155111; decodes custom errors."],
        ["scripts/deploy.js", "Deploys MockUSDC then AgentVault(token); prints addresses, tx hashes and Etherscan links; optional verification."],
        ["scripts/demo.js", "End-to-end demo; deploys or attaches (TOKEN_ADDRESS, VAULT_ADDRESS); expected-to-fail calls are simulated with staticCall so they cost no gas."],
        [".env.example", "Placeholders only; the real `.env` is git-ignored."],
        ["report/diagrams/render.js", "Builds the figures of this report as SVG and renders them to PNG."],
        ["report/generate_report.py", "Builds this report from the real output files."],
    ],
    [3, 7],
    code_cols=(0,),
)
heading("7.4 Gas Measurements", 2)
para(
    f"Table {next_tab()} lists the gas used by each function, measured with hardhat-gas-reporter on the local "
    "Hardhat network over a subset of the tests (saved in `report/gas_report.txt`). The reporter notes that the "
    "method figures are execution gas and do not include the intrinsic transaction overhead. `pay()` is the most "
    "expensive call because it writes a new `PaymentRequest` including the memo string to storage."
)
table(
    "Gas used per function (local Hardhat network)",
    ["Contract / function", "Min", "Max", "Average", "Calls"],
    [[f"AgentVault.{r[0]}" if r[0] not in ("approve", "mint") else f"MockUSDC.{r[0]}", r[1], r[2], r[3], r[4]] for r in gas_methods]
    + [[f"deploy {d[0]}", "-", "-", d[3], "-"] for d in gas_deploy],
    [4, 1.5, 1.5, 1.6, 1.2],
    code_cols=(0,),
)

# ================================================================== 8 TESTING
heading("8. Testing", 1)
heading("8.1 Unit Tests", 2)
para(
    "The tests use Hardhat's local network, chai with the Hardhat chai matchers, and the network helpers "
    "`loadFixture` (each test starts from the same snapshot) and `time` (to move the clock for the window "
    f"and expiry rules). `npx hardhat test` reports **{TESTS_PASSING} passing**"
    + (f" and {TESTS_FAILING} failing" if TESTS_FAILING else " and none failing")
    + f". Table {next_tab()} groups them; the counts are taken from `report/test_output.txt`."
)
GROUP_TEXT = {
    "MockUSDC": "name, symbol, 6 decimals; only owner can mint",
    "deployment": "token and owner set; zero token rejected; renounceOwnership disabled",
    "deposit": "anyone can deposit, event and balances; zero amount; missing allowance",
    "withdraw": "owner only; event; zero address/amount; insufficient balance; works while paused",
    "setAgentPolicy": "stored values and event; zero agent; invalid limits; expiry not in future; non-owner; update keeps window usage; lowered limit gives zero remaining",
    "payee allowlist": "event and toggle; zero/vault payee rejected; non-owner; non-allowlisted payee; lists are per agent",
    "pay: under threshold (auto-execute)": "executes, stores request, event args, balances; returns id; zero amount; memo 140/141 bytes; insufficient vault balance",
    "pay: limits": "perTx limit; amount > uint128; daily limit; window reset after 24 h (time travel, both sides of the boundary)",
    "expiry, revoke, pause": "expiry boundary; revoke and double revoke; non-owner revoke; unknown address; pause/unpause",
    "approval flow (human-in-the-loop)": "Pending with no transfer; threshold boundary; approve and reject with events; finality; access control; re-checks (revoked, expired, payee removed, perTx lowered, window used, balance); pause blocks approve",
    "reentrancy": "malicious token re-enters pay() during pay() and withdraw(): blocked",
    "property-style: random amounts never exceed dailyLimit per window": "300 random payments/approvals with random time jumps (seeded)",
}
rows = []
for g, n in groups.items():
    rows.append([g, str(n), GROUP_TEXT.get(g, "")])
rows.append(["Total", str(TESTS_PASSING), "all passing" if not TESTS_FAILING else f"{TESTS_FAILING} failing"])
table("Unit tests by group", ["Group", "Tests", "What is covered"], rows, [3.2, 0.9, 6])
para(
    "A typical test checks the custom error and its arguments. For example, the re-check at approval time "
    "after the agent has been revoked:"
)
t_src = need(ROOT / "test" / "AgentVault.test.js")
i = t_src.index('it("re-check at approval: agent revoked after request"')
j = t_src.index("    });", i) + len("    });")
code("\n".join(l[4:] for l in t_src[i:j].splitlines()))
heading("8.2 Property-Style Test", 2)
para(
    "The last test drives 300 steps with a seeded pseudo-random generator, so a failure can be reproduced. "
    "In each step it may jump the clock forward between one minute and 30 hours, then the agent pays a random "
    "amount between one base unit and 120 mUSDC (some above the 100 mUSDC per-payment limit); Pending "
    "requests are approved with probability 0.7. After every step it checks `spentInWindow <= dailyLimit` from "
    "the contract state. At the end it checks two more things independently of the contract's own counter: "
    "the payee's balance equals the sum of all Executed requests, and replaying the `PaymentExecuted` events "
    "with their block timestamps never puts more than `dailyLimit` into one window. It also asserts that some "
    "calls were actually rejected, so the limits were exercised."
)
heading("8.3 Reentrancy Test", 2)
para(
    "`contracts/test/ReentrantToken.sol` is a test-only ERC-20 whose `transfer` calls `vault.pay()` again "
    "while the vault is still inside `pay()` or `withdraw()`. The token contract is registered as an agent so "
    "that its call would pass every policy check. Both outer calls revert with OpenZeppelin's "
    "`ReentrancyGuardReentrantCall`, which shows that the guard, not luck, stops the attack. This helper is "
    "never deployed and is excluded from coverage."
)
heading("8.4 Coverage", 2)
cv = [[k] + v for k, v in cov.items()]
table("Coverage from npx hardhat coverage (solidity-coverage 0.8.17)", ["File", "% Stmts", "% Branch", "% Funcs", "% Lines"], cv, [3, 1.5, 1.5, 1.5, 1.5])
para(
    "The three uncovered branches in AgentVault.sol are the \"already entered\" branch of `nonReentrant` on "
    "`deposit`, `withdraw` and `approveRequest`; the reentrancy test re-enters `pay()` only. High coverage "
    "means the code was executed by tests; it does not prove the code is correct."
)
heading("8.5 Static Analysis with Slither", 2)
para(
    f"Slither 0.9.3 [14] ran {SLITHER_DET} detectors on the contracts (OpenZeppelin and test helpers "
    f"filtered out) and reported {SLITHER_N} results (raw output in `report/slither_output.txt`)."
)
table(
    "Slither findings and assessment",
    ["Detector", "Count", "Assessment"],
    [
        ["timestamp", str(slither_ts), "Intended: expiry and the 24 h window depend on block time. Block producers can shift timestamps only slightly, which is negligible against 24 h. One hit (`id >= requests.length`) is a false positive."],
        ["solc-version", str(slither_ver), "Informational: 0.8.28 is called \"too recent\". It is kept because the course setup fixes it; see the compiler bug check in Section 10.4."],
    ],
    [2, 1, 7],
    code_cols=(0,),
)
heading("8.6 Local Demo", 2)
para(
    "`npx hardhat run scripts/demo.js` runs the whole scenario on the local network: the owner deploys, mints "
    "and deposits 1000 mUSDC, sets a policy (per payment 100, window 250, approval above 50, expiry 7 days) "
    "and allows one payee. The agent then (1) pays 20 to the payee, which executes; (2) tries to pay a "
    "random, non-allowlisted address, which the contract rejects with `PayeeNotAllowed`; (3) tries to pay 150, "
    "rejected with `ExceedsPerTxLimit`; and (4) requests 80, which becomes Pending until the owner approves it. "
    "The recorded output is reproduced below from `report/demo_output_local.txt`, unchanged except that long "
    "lines are wrapped; the addresses are Hardhat's public development accounts."
)
code(demo_local, size=7, keep=False)

# ================================================================== 9 DEPLOYMENT
heading("9. Deployment", 1)
heading("9.1 Compiler Settings and Procedure", 2)
para(
    "The contracts are deployed to the Sepolia test network (chain id 11155111), which uses test ETH with "
    "no value. Two routes are documented in the repository. In the first, the owner deploys with Remix IDE and "
    "MetaMask by following `docs/DEPLOY_REMIX.md`; no private key leaves the wallet [16]. In the second, "
    "`scripts/deploy.js` deploys with a test-only key read from the local `.env` file. In both cases the "
    f"settings in Table {next_tab()} must be used."
)
table(
    "Settings that must match in Hardhat, Remix and Etherscan",
    ["Setting", "Value"],
    [
        ["Compiler", "v0.8.28+commit.7893614a"],
        ["Optimization", "enabled, 200 runs"],
        ["EVM version", "cancun"],
        ["License", "MIT"],
        ["Remix environment", "Browser Extension (MetaMask), network Sepolia (11155111)"],
        ["Etherscan verification", "Solidity (Single file) with the flattened source in `flat/` [17]"],
    ],
    [3, 7],
)
para(
    "For Remix the repository provides flattened files (`flat/*.sol`) made with `hardhat flatten`. They were "
    "compiled with solc-js 0.8.28 at the same settings: the runtime bytecode is identical to the Hardhat build "
    "except for the metadata hash, which depends on the file layout. Deploying the flattened file and verifying "
    "the same file on Etherscan therefore gives an exact match. MockUSDC is deployed first, then "
    "AgentVault with the MockUSDC address as constructor argument."
)
placeholder("Remix Solidity Compiler panel showing 0.8.28, optimization 200 runs, EVM cancun")
placeholder("MetaMask confirmation dialog for the AgentVault deployment on Sepolia")
heading("9.2 Sepolia Deployment", 2)
if DEP:
    table(
        "Contracts deployed on Sepolia",
        ["Contract", "Address", "Deployment transaction"],
        [
            ["MockUSDC", DEP["MockUSDC"]["address"], DEP["MockUSDC"]["tx"]],
            ["AgentVault", DEP["AgentVault"]["address"], DEP["AgentVault"]["tx"]],
        ],
        [1.6, 4.2, 4.2],
        code_cols=(1, 2),
    )
    para(f"Owner (deployer) address: `{DEP['deployer']}`. Etherscan pages:")
    bullets([
        f"MockUSDC: {DEP['MockUSDC']['explorer']}",
        f"AgentVault: {DEP['AgentVault']['explorer']}",
    ])
else:
    para("The contracts are deployed on Sepolia with the following addresses and transactions:")
    table(
        "Contracts deployed on Sepolia",
        ["Contract", "Address", "Deployment transaction"],
        [
            ["MockUSDC", "[to be filled]", "[to be filled]"],
            ["AgentVault", "[to be filled]", "[to be filled]"],
        ],
        [1.6, 4.2, 4.2],
    )
    todo("contract addresses, transaction hashes and Etherscan links (re-run report/generate_report.py "
         "after deployments/sepolia.json exists)")
placeholder("Sepolia Etherscan page of AgentVault showing the verified source (green check)")
heading("9.3 Demo on Sepolia", 2)
para(
    "The same demo script runs against the deployed contracts with `--network sepolia`. On Sepolia the agent "
    "is a second, throwaway account with a little test ETH for gas; its key exists only in the local `.env` "
    "file. The expected-to-fail calls are simulated with `staticCall`, so they cost no gas and do not appear as "
    "failed transactions."
)
if DEMO_SEP:
    code(DEMO_SEP, size=7, keep=False)
else:
    todo("output of `npx hardhat run scripts/demo.js --network sepolia` (report/demo_output_sepolia.txt)")
placeholder("Etherscan transaction list of the vault showing pay() and approveRequest() on Sepolia")

# ================================================================== 10 SECURITY
heading("10. Security Analysis", 1)
heading("10.1 Threat Model", 2)
para(
    "The assets are the tokens in the vault. The owner is trusted. The agent is **not** trusted: its prompt, "
    "code and key are assumed to be possibly under an attacker's control, which matches the risks named by "
    f"QuillAudits [11]. Payees are trusted only as far as the owner allowlists them. Table {next_tab()} lists "
    "the threats and the controls."
)
table(
    "Threats and how AgentVault handles them",
    ["Threat", "Control in AgentVault", "Tested"],
    [
        ["Prompt-injected agent or stolen agent key", "Loss bounded by perTx, window limit, allowlist and expiry; large payments need the owner.", "Yes"],
        ["Agent pays an attacker address", "Per-agent payee allowlist (PayeeNotAllowed).", "Yes"],
        ["Many small payments add up", "Fixed 24 h window limit (ExceedsDailyLimit).", "Yes, incl. random test"],
        ["Agent keeps spending after the task", "Expiry and revokeAgent.", "Yes"],
        ["Stale approval of an old request", "approveRequest re-checks the whole policy.", "Yes (6 cases)"],
        ["Reentrancy through token callbacks", "nonReentrant on every token-moving function; checks-effects-interactions.", "Yes (malicious token)"],
        ["Silent token transfer failure", "SafeERC20 reverts on failure.", "Indirectly"],
        ["Emergency (bug or attack in progress)", "pause() stops pay and approve; withdraw and reject still work.", "Yes"],
        ["Owner loses or renounces control", "renounceOwnership disabled.", "Yes"],
        ["Owner key compromised", "Not mitigated: the owner has full control (future work: multisig).", "-"],
        ["Burst at window boundary", "Not mitigated: fixed window allows up to 2 x dailyLimit (Section 6.6).", "-"],
    ],
    [3.2, 5.2, 1.6],
)
heading("10.2 Mitigations in the Code", 2)
bullets([
    "**Checks-effects-interactions:** all checks and state updates (window, request record, events) happen "
    "before `safeTransfer`.",
    "**`nonReentrant`** on `deposit`, `withdraw`, `pay` and `approveRequest`.",
    "**SafeERC20** for all token transfers.",
    "**Input validation** on every owner function and in `pay()`: zero addresses, zero amounts, limit order, "
    "expiry in the future, memo length, payee not the vault itself.",
    "**Custom errors with arguments** instead of strings: cheaper, and the reason for a failure is visible.",
    "**Testnet guard in scripts:** the deploy and demo scripts refuse every chain except Hardhat and Sepolia.",
    "**No secrets in the repository:** keys only in a git-ignored `.env`; `.env.example` contains placeholders.",
])
heading("10.3 Known Limitations", 2)
numbered([
    "The owner is a single externally owned account with full control over funds and policies.",
    "The window is fixed, not rolling (Section 6.6).",
    "An agent can create any number of Pending requests. They move no funds but fill `requests[]` and the "
    "owner's review queue; requests do not expire.",
    "A Pending request is not reserved against the window or the balance, so its approval may fail later.",
    "The memo is public and permanent; it must not contain secrets or personal data, and off-chain tools "
    "must treat it as untrusted text.",
    "Only a standard ERC-20 (MockUSDC) was tested. Fee-on-transfer, rebasing or blocklisting tokens could "
    "behave differently.",
    "The contract is not upgradeable; a bug requires a new deployment and moving the funds with `withdraw`.",
])
heading("10.4 Compiler Known-Bugs Check", 2)
para(
    "The Solidity team publishes a machine-readable list of known compiler bugs [15]. On 17 November 2026 it "
    "listed seven bugs that affect 0.8.28. This build uses the legacy code generator (no `viaIR`), the "
    f"optimizer and EVM version cancun. Table {next_tab()} gives the assessment."
)
table(
    "Known solc 0.8.28 bugs and whether they apply to this build",
    ["Bug", "Severity", "Fixed in", "Applies here?"],
    [
        ["TransientStorageClearingHelperCollision", "high", "0.8.34", "No (needs viaIR)"],
        ["UnsoundSpillInMutualRecursion", "medium", "0.8.36", "No (needs viaIR)"],
        ["SpillSlotCollisionAcrossMutualRecursion", "low/medium", "0.8.37", "No (needs viaIR)"],
        ["MisorderedNamedParametersInRequireWithCustomErrors", "very low", "0.8.37", "No (needs viaIR)"],
        ["MemoryByteArrayElementDeleteClearsWholeWord", "low/medium", "0.8.37", "No (no delete on memory bytes elements)"],
        ["YulOptimizerKnowledgeBaseStaleBookkeeping", "low", "0.8.38", "Not ruled out (optimizer on; SafeERC20 has inline assembly)"],
        ["LostStorageArrayWriteOnSlotOverflow", "low", "0.8.32", "Not ruled out formally; not practically reachable for requests[]"],
    ],
    [4.4, 1.4, 1.2, 3.4],
    code_cols=(0,),
)
para(
    "None of the bugs that clearly apply is rated above low, but two cannot be ruled out without a deeper "
    "analysis. Before any use beyond this course, the contracts should be recompiled with the newest 0.8.x "
    "release and all tests run again."
)
heading("10.5 What Still Needs Review", 2)
para(
    "The tests, coverage and Slither results reduce risk but do not prove the contract is safe. The following "
    "is still open: an independent line-by-line review by someone other than the author; confirmation that the "
    "two compiler bugs above do not affect the bytecode; a decision on expiring or capping Pending requests; a "
    "gas review of storing memo strings; triage of the 39 `npm audit` advisories in the development tool chain; "
    "and, for any real-money use, a professional audit and a multisig owner."
)

# ================================================================== 11 LIMITATIONS & FUTURE WORK
heading("11. Limitations and Future Work", 1)
heading("11.1 Limitations", 2)
bullets([
    "Testnet only, with a test token. No real agent framework is connected; the agent is a script with a key.",
    "One token per vault and one owner key.",
    "Policy and approvals are managed by calling the contract directly (Remix, Etherscan or scripts); there is "
    "no user interface for the owner.",
    "No measurements on mainnet gas prices or under load were made.",
])
heading("11.2 Future Work", 2)
numbered([
    "**ERC-4337 session-key module.** Move the policy into a smart-account validation module so the agent "
    "uses a limited session key of the owner's own smart account instead of a separate vault [4], [9].",
    "**EIP-7702 delegation.** Let the owner's existing EOA delegate to code that enforces the same policy, "
    "which the EIP lists as a use case (privilege de-escalation) [5].",
    "**ERC-8004 identity.** Accept only agents registered in an ERC-8004 Identity Registry, and possibly scale "
    "limits with their reputation [6], [7].",
    "**Multisig owner.** Make the owner a multisig or a timelock so that one stolen key cannot drain the vault.",
    "**Stablecoin integration and x402.** Use a real testnet stablecoin and let the agent pay x402-style "
    "invoices from the vault, handling tokens with blocklists [8], [9].",
    "**Rolling window and request expiry.** Replace the fixed window with a rolling one, give Pending "
    "requests an expiry, and cap their number per agent.",
    "**Owner dashboard.** A small interface that lists Pending requests and their memos for review.",
])

# ================================================================== 12 CONCLUSION
heading("12. Conclusion", 1)
para(
    "AgentVault shows that the spending limits for an AI agent can be enforced by a smart contract instead of "
    "by the agent's own instructions. The owner sets a per-payment limit, a limit per 24-hour window, an "
    "approval threshold, an expiry and a payee allowlist; the contract executes small payments, holds large "
    "ones for a human decision, and re-checks the policy when the human approves. In the demo, the contract "
    "rejected a payment to an unknown address and a payment above the per-payment limit, and held a large "
    "payment until the owner approved it."
)
para(
    f"All {TESTS_PASSING} tests pass, coverage of AgentVault.sol is {a[0]} % of statements and {a[1]} % of "
    f"branches, and Slither reported {SLITHER_N} low or informational findings. The work also made the "
    "limits of the approach visible: the owner key is a single point of control, the fixed window allows a "
    "burst at its boundary, and pending requests are not bounded. These, together with the compiler version "
    "question, are listed as open points. The project is a course case study on a testnet; it has not been "
    "audited."
)

# ================================================================== REFERENCES
heading("References", 1)
REFS = [
    'V. Buterin, "Ethereum Whitepaper: A Next-Generation Smart Contract and Decentralized Application Platform," 2014. [Online]. Available: https://ethereum.org/en/whitepaper/',
    'Solidity Team, "Solidity Documentation," v0.8.38. [Online]. Available: https://docs.soliditylang.org/',
    'F. Vogelsteller and V. Buterin, "ERC-20: Token Standard," Ethereum Improvement Proposals, no. 20, Nov. 2015. [Online]. Available: https://eips.ethereum.org/EIPS/eip-20',
    'V. Buterin, Y. Weiss, D. Tirosh, S. Nacson, A. Forshtat, K. Gazso and T. Hess, "ERC-4337: Account Abstraction Using Alt Mempool," Ethereum Improvement Proposals, no. 4337, Sep. 2021. [Online]. Available: https://eips.ethereum.org/EIPS/eip-4337',
    'V. Buterin, S. Wilson, A. Dietrichs and lightclient, "EIP-7702: Set Code for EOAs," Ethereum Improvement Proposals, no. 7702, May 2024. [Online]. Available: https://eips.ethereum.org/EIPS/eip-7702',
    'M. De Rossi, D. Crapis, J. Ellis and E. Reppel, "ERC-8004: Trustless Agents," Ethereum Improvement Proposals, no. 8004, Aug. 2025 (Draft). [Online]. Available: https://eips.ethereum.org/EIPS/eip-8004',
    'ERC-8004 team, "erc-8004-contracts: Registry contracts curated by the 8004 team," GitHub repository. [Online]. Available: https://github.com/erc-8004/erc-8004-contracts',
    'Chainlink, "Agent Payment Standards and x402," last updated Jun. 23, 2026. [Online]. Available: https://chain.link/article/agent-payment-standards-x402',
    'bcNeutron, "AI Agent Wallets: How Autonomous Software Gets a Crypto Bank Account," Spark Research, Oct. 20, 2026. [Online]. Available: https://www.spark.money/research/ai-agent-wallet-policy-architecture',
    'N. Hodge, "Who\'s Actually Paying? Measuring AI Agent Payments Onchain," TRM Labs Tech Blog, Sep. 9, 2026. [Online]. Available: https://www.trmlabs.com/trm-tech-blog/whos-actually-paying-measuring-ai-agent-payments-onchain',
    'QuillAudits Team, "Agentic Wallet Security: Session Keys, Spending Caps, and Risks," Aug. 30, 2026. [Online]. Available: https://www.quillaudits.com/blog/web3-security/Agentic-Wallet-Security',
    'OpenZeppelin, "Contracts 5.x Documentation." [Online]. Available: https://docs.openzeppelin.com/contracts/5.x/',
    'Nomic Foundation, "Hardhat Documentation" (Hardhat 3) and "Hardhat 2 Documentation." [Online]. Available: https://hardhat.org/docs and https://v2.hardhat.org/hardhat-runner/docs/getting-started',
    'Crytic (Trail of Bits), "Slither: Static Analyzer for Solidity and Vyper," GitHub repository. [Online]. Available: https://github.com/crytic/slither',
    'Solidity Team, "List of Known Bugs." [Online]. Available: https://docs.soliditylang.org/en/latest/bugs.html',
    'Remix Project, "Remix IDE Documentation: Compiler, Deploy & Run, Importing Files." [Online]. Available: https://remix-ide.readthedocs.io/en/latest/',
    'Etherscan, "Verify & Publish Contract Source Code (Sepolia)." [Online]. Available: https://sepolia.etherscan.io/verifyContract',
]
for k, ref in enumerate(REFS, 1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(1.0)
    pf.first_line_indent = Cm(-1.0)
    pf.tab_stops.add_tab_stop(Cm(1.0))
    pf.space_after = Pt(6)
    pf.line_spacing = Pt(16)
    p.add_run(f"[{k}]\t{ref}").font.size = Pt(11)
p = para("All online sources were opened and checked on 17 November 2026.", after=0)
p.runs[0].italic = True

# ================================================================== APPENDIX A
heading("Appendix A: Setup and Run Steps", 1)
para("These steps are taken from the project README. They need Node.js 20 or later.")
code(
    "git clone <repository-url> agentvault && cd agentvault\n"
    "npm install\n"
    "npx hardhat compile\n"
    "npx hardhat test                 # " + f"{TESTS_PASSING} passing\n"
    "npx hardhat coverage\n"
    "npx hardhat run scripts/demo.js  # local demo\n"
    "\n"
    "# optional static analysis (Python)\n"
    "pip install slither-analyzer\n"
    "python -m slither . --filter-paths \"node_modules|contracts/test\"\n"
    "\n"
    "# Sepolia (test-only keys in a local .env, never committed)\n"
    "cp .env.example .env\n"
    "npx hardhat run scripts/deploy.js --network sepolia\n"
    "npx hardhat run scripts/demo.js --network sepolia\n"
    "\n"
    "# rebuild this report\n"
    "node report/diagrams/render.js\n"
    "python report/generate_report.py"
)

# ================================================================== APPENDIX B
heading("Appendix B: Selected Code Listing", 1)
para("**MockUSDC.sol** (complete):")
code(mock_src.strip(), size=8, keep=False)
para("**AgentVault.sol**, internal helpers:")
for sig in ("function _checkAgent(", "function _remaining(", "function _checkBalance(", "function _pendingRequest("):
    code(extract_function(contract_src, sig), size=8)
para("The full source is in `contracts/AgentVault.sol` in the repository.")

# ------------------------------------------------------------------ fill the lists
for k, f in enumerate(FIGS, 1):
    p = figs_marker.insert_paragraph_before(f"Figure {k}: {f}")
    p.paragraph_format.space_after = Pt(3)
for k, t in enumerate(TABS, 1):
    p = tabs_marker.insert_paragraph_before(f"Table {k}: {t}")
    p.paragraph_format.space_after = Pt(3)

doc.save(OUT)

todo_md = ["# Screenshots to insert in AgentVault_Report.docx", "",
           "Each item has a dashed placeholder box in the report. Replace the box with the screenshot "
           "(Insert > Pictures) and keep the surrounding text.", ""]
todo_md += [f"- [ ] {s}" for s in SHOTS]
if not DEP:
    todo_md += ["", "Also pending (filled automatically when `deployments/sepolia.json` exists and the report is regenerated):",
                "- [ ] Sepolia addresses, tx hashes and Etherscan links (Section 9.2)"]
if not DEMO_SEP:
    todo_md += ["- [ ] Sepolia demo output `report/demo_output_sepolia.txt` (Section 9.3)"]
(REP / "SCREENSHOTS_TODO.md").write_text("\n".join(todo_md) + "\n", encoding="utf-8")

print(f"wrote {OUT.relative_to(ROOT)}: {len(FIGS)} figures, {len(TABS)} tables, {len(REFS)} references, "
      f"{len(SHOTS)} screenshot placeholders; tests={TESTS_PASSING}, slither={SLITHER_N}, "
      f"sepolia={'yes' if DEP else 'pending'}")
