"""Draws three images of the README in the colours of DESIGN.md:
- steps.svg: the review in three steps (the problems, the readings, the answer);
- chain.svg: who invites whom in RightFit online;
- way_in.svg: how a person gets into a project online.
The values shown are P01's, as read in data/maf/extracted/P01.json; no project, client or person is named.
Run from this folder: python make_diagrams.py. Without motion (prefers-reduced-motion) each drawing shows its finished state."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'Courier New', Courier, monospace"
INK, INK2, LABEL, GREY = "#15191A", "#3D4A42", "#4A5D51", "#A9BBAF"
GROUND, BAND, SHEET, LINE, SOFT, RULE = "#E7F0E8", "#DCE9DF", "#FFFFFF", "#C5D6CA", "#E5EDE7", "#B9CDBF"
GREEN, CARBON, CARBON_LINE, RED, RED_WASH = "#0E3B2E", "#4A32B8", "#DAD5F2", "#C4311E", "#FBEDEA"
LOOP = 12  # seconds
EASE, GLIDE = "cubic-bezier(.16,1,.3,1)", "cubic-bezier(.65,0,.35,1)"


class Drawing:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.css, self.body = [], []

    def anim(self, name, frames, ease=EASE):
        self.css.append(f".{name}{{animation:{name} {LOOP}s {ease} infinite}}@keyframes {name}{{{frames}}}")
        return name

    def appear(self, name, at, move="translateY(8px)"):
        """Hidden until `at` % of the loop, in place 4 % later, gone again at the end of the loop."""
        return self.anim(name, f"0%,{at}%{{opacity:0;transform:{move}}}{at + 4}%,93%{{opacity:1;transform:none}}"
                               f"98%,100%{{opacity:0;transform:none}}")

    def draw_in(self, name, start, end):
        """A line or path with pathLength='1' and stroke-dasharray='1', drawn from `start` to `end` % of the loop."""
        # hidden as well until it starts: a round line end would otherwise show as a dot
        return self.anim(name, f"0%,{start}%{{stroke-dashoffset:1;opacity:0}}{start + 0.5}%{{opacity:1}}"
                               f"{end}%,93%{{stroke-dashoffset:0;opacity:1}}98%,100%{{stroke-dashoffset:0;opacity:0}}", GLIDE)

    def add(self, *parts):
        self.body.extend(parts)

    def save(self, name, title, desc):
        svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {self.w} {self.h}' width='{self.w}' height='{self.h}' "
               f"role='img' aria-labelledby='t d' font-family=\"{SANS}\">\n<title id='t'>{title}</title><desc id='d'>{desc}</desc>\n"
               f"<style>{''.join(self.css)}.land{{transform-box:fill-box;transform-origin:center}}"
               f"@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>\n"
               f"<rect width='{self.w}' height='{self.h}' fill='{GROUND}'/>\n" + "\n".join(self.body) + "\n</svg>\n")
        (HERE / name).write_text(svg, encoding="utf-8")
        print(name, len(svg), "bytes")


def steps_row(d, steps, runs, x0, step, width, title_size, y=40):
    """Numbered steps along a line: a green dot runs along each step's rule and inks its title as it passes."""
    for i, ((title, lines), (a, b)) in enumerate(zip(steps, runs)):
        x = x0 + i * step
        d.add(f"<line x1='{x}' y1='{y}' x2='{x + width}' y2='{y}' stroke='{RULE}' stroke-width='2'/>",
              f"<line class='{d.draw_in(f'rule{i}', a, b)}' pathLength='1' stroke-dasharray='1' x1='{x}' y1='{y}' "
              f"x2='{x + width}' y2='{y}' stroke='{GREEN}' stroke-width='3'/>",
              f"<text x='{x}' y='{y + 34}' font-size='14' fill='{LABEL}' letter-spacing='1.5'>0{i + 1}</text>")
        ink = d.anim(f"title{i}", f"0%,{a}%{{fill:{GREY}}}{a + 3}%,93%{{fill:{INK}}}99%,100%{{fill:{GREY}}}")
        d.add(f"<text class='{ink}' x='{x}' y='{y + 70}' font-size='{title_size}' font-weight='700' fill='{INK}' "
              f"letter-spacing='-0.4'>{title}</text>")
        for k, line in enumerate(lines):
            d.add(f"<text x='{x}' y='{y + 98 + k * 22}' font-size='17' fill='{INK2}'>{line}</text>")
    last = x0 + (len(steps) - 1) * step + width   # the dot rests at the end of the last rule
    moves = "".join(f"{a}%{{transform:translateX({x0 + i * step - last}px)}}{b}%{{transform:translateX({x0 + i * step + width - last}px)}}"
                    for i, (a, b) in enumerate(runs))
    dot = d.anim("dot", f"0%{{transform:translateX({x0 - last}px);opacity:0}}3%{{opacity:1}}{moves}"
                        f"93%{{transform:none;opacity:1}}98%,100%{{transform:none;opacity:0}}", GLIDE)
    d.add(f"<circle class='{dot}' cx='{last}' cy='{y}' r='8' fill='{GREEN}'/>")


def sheet(x, y, w, h):
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{SHEET}' stroke='{LINE}' stroke-width='1.5'/>"


def review_steps():
    d = Drawing(1200, 392)
    x0, step, width = 40, 387, 345
    steps = [("The problems", ("each one beside its page,", "with the quoted line marked")),
             ("The readings", ("violet and dashed: the AI read it;", "black and solid: a person confirmed it")),
             ("The answer", ("A, B or C, one comment per issue,", "ready to copy; a person signs"))]
    steps_row(d, steps, [(4, 12), (34, 42), (62, 70)], x0, step, width, 28)
    top = 182

    # 01: a page of the declaration with the product line marked, and the finding beside it
    x = x0
    d.add(sheet(x, top, width, 180))
    page = d.appear("page", 6)
    bars = "".join(f"<rect x='{x + 26}' y='{226 + j * 14}' width='{(84, 70, 88, 76, 62, 86, 72, 80)[j]}' height='5' fill='{LINE if j else BAND}'/>"
                   for j in range(8))
    d.add(f"<g class='{page}'><rect x='{x + 16}' y='{top + 16}' width='104' height='148' fill='{SHEET}' stroke='{LINE}' stroke-width='1.5'/>"
          f"<rect x='{x + 26}' y='{top + 26}' width='48' height='8' fill='{INK2}'/>{bars}</g>")
    mark = d.appear("mark", 11, "translateX(-6px)")
    d.add(f"<g class='{mark}'><rect x='{x + 20}' y='{263}' width='96' height='15' fill='{RED_WASH}'/>"
          f"<rect x='{x + 20}' y='263' width='3' height='15' fill='{RED}'/><rect x='{x + 26}' y='268' width='76' height='5' fill='{RED}'/></g>")
    find = d.appear("find", 14, "translateX(10px)")
    d.add(f"<g class='{find}'><rect x='{x + 136}' y='{top + 16}' width='30' height='20' fill='none' stroke='{RED}' stroke-width='1.5'/>"
          f"<text x='{x + 151}' y='{top + 31}' font-size='12' font-weight='700' fill='{RED}' text-anchor='middle'>D2</text>"
          f"<text x='{x + 136}' y='{top + 58}' font-size='15' font-weight='700' fill='{INK}'>Declaration matches</text>"
          f"<text x='{x + 136}' y='{top + 76}' font-size='15' font-weight='700' fill='{INK}'>the products</text>"
          f"<text x='{x + 136}' y='{top + 100}' font-size='13' fill='{INK2}'>it names SL1 and SLV,</text>"
          f"<text x='{x + 136}' y='{top + 117}' font-size='13' fill='{INK2}'>none of the items submitted</text>"
          f"<text x='{x + 136}' y='{top + 142}' font-size='12' fill='{LABEL}'>rule EU-MACH-DOC</text>"
          f"<text x='{x + 136}' y='{top + 158}' font-size='12' fill='{LABEL}'>verified official</text></g>")
    d.add(f"<path class='{d.draw_in('link', 16, 20)}' pathLength='1' stroke-dasharray='1' d='M{x + 116} 270 H{x + 128}' "
          f"stroke='{RED}' stroke-width='2' fill='none'/>")

    # 02: two readings of P01's booster set; the first is confirmed, the second still waits
    x = x0 + step
    d.add(sheet(x, top, width, 180))
    rows = [("DUTY POINT", "15 m³/h at 50 m", "the form, page 1", 190, True),
            ("MAX. PRESSURE", "10 bar", "the data sheet, page 2", 66, False)]
    for r, (label, value, source, length, confirmed) in enumerate(rows):
        y = top + 28 + r * 84
        show = d.appear(f"row{r}", 36 + r * 3)
        colour = (d.anim("confirm", f"0%,49%{{fill:{CARBON}}}53%,100%{{fill:{INK}}}") if confirmed else "")
        d.add(f"<g class='{show}'><text x='{x + 20}' y='{y}' font-size='11' font-weight='700' fill='{LABEL}' letter-spacing='1.4'>{label}</text>"
              f"<text class='{colour}' x='{x + 20}' y='{y + 28}' font-family=\"{MONO}\" font-size='20' font-weight='700' "
              f"fill='{INK if confirmed else CARBON}'>{value}</text>"
              f"<line x1='{x + 20}' y1='{y + 37}' x2='{x + 20 + length}' y2='{y + 37}' stroke='{CARBON}' stroke-width='2' stroke-dasharray='5 4'/>"
              f"<text x='{x + 20}' y='{y + 56}' font-size='12' fill='{LABEL}'>{source}</text>"
              f"<rect x='{x + 300}' y='{y + 10}' width='22' height='22' fill='{SHEET}' stroke='{INK if confirmed else LINE}' stroke-width='1.5'/></g>")
        if confirmed:
            d.add(f"<line class='{d.draw_in('solid', 51, 55)}' pathLength='1' stroke-dasharray='1' x1='{x + 20}' y1='{y + 37}' "
                  f"x2='{x + 20 + length}' y2='{y + 37}' stroke='{INK}' stroke-width='2.5'/>",
                  f"<path class='{d.draw_in('tick', 49, 52)}' pathLength='1' stroke-dasharray='1' d='M{x + 305} {y + 21} l5 6 l9 -11' "
                  f"fill='none' stroke='{INK}' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/>")

    # 03: the draft answer, its comments, the copy button and the signature
    x = x0 + 2 * step
    d.add(sheet(x, top, width, 180))
    stamp = d.anim("stamp", "0%,64%{opacity:0;transform:scale(1.6)}67%,93%{opacity:1;transform:scale(1)}98%,100%{opacity:0;transform:scale(1)}")
    d.add(f"<g transform='rotate(-6 {x + 64} {top + 64})'><g class='{stamp} land'>"
          f"<rect x='{x + 22}' y='{top + 22}' width='84' height='84' fill='none' stroke='{RED}' stroke-width='4'/>"
          f"<text x='{x + 64}' y='{top + 86}' font-family=\"{MONO}\" font-size='64' font-weight='700' fill='{RED}' text-anchor='middle'>B</text></g></g>")
    d.add(f"<text class='{d.appear('noted', 69)}' x='{x + 128}' y='{top + 34}' font-size='12' font-weight='700' fill='{LABEL}' "
          f"letter-spacing='1.4'>APPROVED AS NOTED</text>")
    for k, length in enumerate((178, 150, 186, 120)):
        d.add(f"<g class='{d.appear(f'comment{k}', 71 + k * 2, 'translateX(-6px)')}'>"
              f"<text x='{x + 128}' y='{top + 59 + k * 18}' font-size='11' fill='{LABEL}'>{k + 1}.</text>"
              f"<rect x='{x + 142}' y='{top + 53 + k * 18}' width='{length}' height='5' fill='{LINE}'/></g>")
    d.add(f"<g class='{d.appear('copy', 80)}'><rect x='{x + 128}' y='{top + 128}' width='142' height='34' fill='{SHEET}' "
          f"stroke='{GREEN}' stroke-width='1.5'/><text x='{x + 199}' y='{top + 150}' font-size='14' font-weight='700' fill='{GREEN}' "
          f"text-anchor='middle'>Copy the answer</text></g>")
    d.add(f"<path class='{d.draw_in('sign', 83, 90)}' pathLength='1' stroke-dasharray='1' "
          f"d='M{x + 24} {top + 146} c8 -18 14 -18 12 0 s10 -16 16 -6 s6 10 14 -4 s8 -6 12 2 c4 6 10 2 22 -6' "
          f"fill='none' stroke='{INK}' stroke-width='2' stroke-linecap='round'/>",
          f"<text class='{d.appear('signs', 88)}' x='{x + 24}' y='{top + 168}' font-size='12' fill='{LABEL}'>a person signs</text>")

    d.save("steps.svg", "The review in three steps: the problems, the readings, the answer",
           "01 The problems: each one beside its page, with the quoted line marked; a declaration page gets its product line "
           "marked in red, and the finding D2, declaration matches the products, says it names SL1 and SLV, none of the items "
           "submitted, under rule EU-MACH-DOC, verified official. 02 The readings: the duty point, 15 m3/h at 50 m from the form, "
           "is violet and dashed until a person ticks it, then black and solid; the maximum pressure, 10 bar from the data sheet, "
           "stays violet. 03 The answer: a red B stamp, approved as noted, four comments, a button to copy the answer, and a "
           "signature: a person signs.")


def node(d, x, y, role, line, cls, w=196, h=66):
    d.add(f"<g class='{cls}'>{sheet(x, y, w, h)}"
          f"<text x='{x + 16}' y='{y + 25}' font-size='12' font-weight='700' fill='{LABEL}' letter-spacing='1.5'>{role}</text>"
          f"<text x='{x + 16}' y='{y + 49}' font-size='14' fill='{INK}'>{line}</text></g>")


def wire(d, name, parent, child, start, w=196, h=66):
    """The elbow from a parent's bottom to a child's top, drawn as the invitation goes out."""
    (px, py), (cx, cy) = parent, child
    mid = (py + h + cy) / 2
    d.add(f"<path class='{d.draw_in(name, start, start + 5)}' pathLength='1' stroke-dasharray='1' "
          f"d='M{px + w / 2} {py + h} V{mid} H{cx + w / 2} V{cy}' fill='none' stroke='{GREEN}' stroke-width='2'/>")


def invitation_chain():
    d = Drawing(1200, 430)
    consultant = (424, 30)
    reviewers = [((64, 160), "DESIGNER", "a reviewer"), ((304, 160), "SITE SUPERVISOR", "a reviewer"),
                 ((544, 160), "CLIENT", "a reviewer"), ((784, 160), "CONTRACTOR", "invites subcontractors")]
    subs = [(664, 300), (904, 300)]
    d.add("<g transform='translate(18 0)'>")   # the tree spans 64 to 1100: centred on the 1200 of the drawing
    node(d, *consultant, "CONSULTANT", "opens the project", d.appear("n0", 3))
    d.add(f"<g class='{d.appear('chip', 7, 'translateX(-8px)')}'>"
          f"<text x='{consultant[0] + 214}' y='{consultant[1] + 26}' font-size='13' fill='{LABEL}'>an invitation is a link for one email,</text>"
          f"<text x='{consultant[0] + 214}' y='{consultant[1] + 44}' font-size='13' fill='{LABEL}'>valid 14 days, sent by the person who invites</text></g>")
    for i, (xy, role, line) in enumerate(reviewers):
        wire(d, f"w{i}", consultant, xy, 10 + i * 3)
        node(d, *xy, role, line, d.appear(f"n{i + 1}", 15 + i * 3))
    for k, xy in enumerate(subs):
        wire(d, f"s{k}", reviewers[3][0], xy, 32 + k * 4)
        node(d, *xy, "SUBCONTRACTOR", "sees its own branch", d.appear(f"sub{k}", 37 + k * 4))
    d.add(f"<g class='{d.appear('apart', 46)}'><line x1='882' y1='300' x2='882' y2='366' stroke='{RED}' stroke-width='2' stroke-dasharray='4 4'/>"
          f"<text x='882' y='392' font-size='13' fill='{INK2}' text-anchor='middle'>a subcontractor never sees another one's branch</text></g>")
    lock = (f"<rect x='86' y='318' width='18' height='14' fill='{GREEN}'/>"
            f"<path d='M89 318 v-5 a6 6 0 0 1 12 0 v5' fill='none' stroke='{GREEN}' stroke-width='2.5'/>")
    d.add(f"<g class='{d.appear('locked', 54)}'>{sheet(64, 296, 520, 54)}{lock}"
          f"<text x='122' y='318' font-size='14' font-weight='700' fill='{INK}'>A locked project</text>"
          f"<text x='122' y='338' font-size='13' fill='{INK2}'>its packages, files, review and BOQ open with the team password as well</text></g>")
    grid = "".join(f"<rect x='{86 + (k % 2) * 10}' y='{372 + (k // 2) * 10}' width='8' height='8' fill='{LABEL}'/>" for k in range(4))
    d.add(f"<g class='{d.appear('manage', 60)}'>{sheet(64, 360, 520, 54)}{grid}"
          f"<text x='122' y='382' font-size='14' font-weight='700' fill='{INK}'>Management</text>"
          f"<text x='122' y='402' font-size='13' fill='{INK2}'>the team that runs RightFit sees people and projects, never the packages</text></g>")
    d.add("</g>")
    d.save("chain.svg", "Who invites whom in RightFit online",
           "The consultant opens the project and invites the designer, the site supervisor and the client, who review, and the "
           "contractor, who invites its subcontractors. An invitation is a link for one email, valid 14 days, sent by the person "
           "who invites. Each subcontractor sees its own branch and never another one's. A locked project opens its packages, files, "
           "review and BOQ only with the team password as well, and Management sees people and projects, never the packages.")


def way_in():
    d = Drawing(1200, 250)
    x0, step, width = 40, 290, 250
    steps = [("Your account", ("Google, or an email", "and a password")),
             ("The terms", ("they open the first time,", "and again when they change")),
             ("Your role", ("an invitation for your email,", "or a project you open")),
             ("The team password", ("for a locked project", "and its own data"))]
    runs = [(4, 13), (19, 28), (34, 43), (49, 58)]
    steps_row(d, steps, runs, x0, step, width, 26)
    y = 176
    x = x0   # 01: two ways in
    for k, (label, dx, w) in enumerate([("Google", 0, 116), ("Email", 130, 104)]):
        d.add(f"<g class='{d.appear(f'in{k}', 6 + k * 3)}'><rect x='{x + dx}' y='{y}' width='{w}' height='44' "
              f"fill='{SHEET if k else GREEN}' stroke='{GREEN}' stroke-width='1.5'/><text x='{x + dx + w / 2}' y='{y + 28}' "
              f"font-size='17' font-weight='700' fill='{GREEN if k else SHEET}' text-anchor='middle'>{label}</text></g>")
    x = x0 + step   # 02: the box gets ticked
    d.add(f"<rect x='{x}' y='{y + 6}' width='32' height='32' fill='{SHEET}' stroke='{INK}' stroke-width='2'/>",
          f"<path class='{d.draw_in('agree', 22, 26)}' pathLength='1' stroke-dasharray='1' d='M{x + 7} {y + 23} l7 7 l12 -14' "
          f"fill='none' stroke='{GREEN}' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/>",
          f"<text x='{x + 46}' y='{y + 29}' font-size='17' fill='{INK}'>I agree</text>")
    x = x0 + 2 * step   # 03: the invitation link and the role it gives
    d.add(f"<g class='{d.appear('link', 37, 'translateX(-8px)')}'>{sheet(x, y, 150, 44)}"
          f"<text x='{x + 14}' y='{y + 28}' font-family=\"{MONO}\" font-size='16' font-weight='700' fill='{INK}'>/join/…</text></g>",
          f"<g class='{d.appear('role', 41, 'translateX(-8px)')}'><rect x='{x + 160}' y='{y + 8}' width='90' height='28' fill='{BAND}'/>"
          f"<text x='{x + 205}' y='{y + 27}' font-size='12' font-weight='700' fill='{LABEL}' letter-spacing='1.2' text-anchor='middle'>CONTRACTOR</text></g>")
    x = x0 + 3 * step   # 04: the password field fills with dots, then the lock opens
    d.add(sheet(x, y, 196, 44))
    for j in range(8):
        d.add(f"<circle class='{d.anim(f'p{j}', f'0%,{50 + j * 0.9:.1f}%{{opacity:0}}{50.4 + j * 0.9:.1f}%,93%{{opacity:1}}98%,100%{{opacity:0}}')}' "
              f"cx='{x + 20 + j * 20}' cy='{y + 22}' r='5' fill='{INK}'/>")
    shackle = d.anim("open", "0%,59%{transform:none}62%,93%{transform:translate(-6px,-5px) rotate(-22deg)}98%,100%{transform:none}")
    d.css.append(".open{transform:translate(-6px,-5px) rotate(-22deg)}")   # without motion the lock shows open, as at the end
    d.add(f"<rect x='{x + 214}' y='{y + 16}' width='26' height='22' fill='{GREEN}'/>",
          f"<path class='{shackle} land' d='M{x + 218} {y + 16} v-6 a9 9 0 0 1 18 0 v6' fill='none' stroke='{GREEN}' stroke-width='3.5'/>")
    d.save("way_in.svg", "How a person gets into a project online",
           "Four steps along a line. 01 Your account: Google, or an email and a password. 02 The terms: they open the first time, "
           "and again when they change; a box gets ticked, I agree. 03 Your role: an invitation for your email, or a project you "
           "open; a link and the role it gives, contractor. 04 The team password, for a locked project and its own data: a field "
           "fills with dots and a lock opens.")


if __name__ == "__main__":
    review_steps()
    invitation_chain()
    way_in()
