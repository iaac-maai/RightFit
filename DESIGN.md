---
name: RightFit
description: An MAF review page drawn like a drawing under review, with numbered revision deltas and markup colors.
colors:
  drafting-ink: "#1D2125"
  ink-secondary: "#464B51"
  ink-tertiary: "#62676D"
  hairline: "#D9DAD5"
  drafting-film: "#F7F7F4"
  sheet-white: "#FFFFFF"
  on-ink: "#FFFFFF"
  on-ink-secondary: "#BCC1C7"
  markup-red: "#D23A2E"
  markup-red-ink: "#B3261E"
  markup-red-wash: "#FBEDEB"
  suggestion-blue: "#2B5FB4"
  suggestion-blue-ink: "#24519C"
  suggestion-blue-wash: "#EDF2FA"
  confirmed-green: "#2F7A4D"
  confirmed-green-wash: "#E9F3ED"
  hold-amber: "#8F5C10"
  hold-amber-wash: "#FAF1E3"
typography:
  display:
    fontFamily: "DIN Condensed, Bahnschrift Condensed, Bahnschrift, Arial Narrow, sans-serif"
    fontSize: "104px"
    fontWeight: 400
    lineHeight: 0.8
  headline:
    fontFamily: "DIN Condensed, Bahnschrift Condensed, Bahnschrift, Arial Narrow, sans-serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.01em"
  title:
    fontFamily: "DIN Condensed, Bahnschrift Condensed, Bahnschrift, Arial Narrow, sans-serif"
    fontSize: "26px"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: "0.02em"
  title-small:
    fontFamily: "DIN Condensed, Bahnschrift Condensed, Bahnschrift, Arial Narrow, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.03em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Segoe UI, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  body-small:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Segoe UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: "DIN Condensed, Bahnschrift Condensed, Bahnschrift, Arial Narrow, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.04em"
  numeral:
    fontFamily: "DIN Alternate, Bahnschrift, -apple-system, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.1
    fontFeature: "\"tnum\""
rounded:
  none: "0px"
  hairline: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  section: "22px"
  gutter: "28px"
components:
  button:
    backgroundColor: "{colors.sheet-white}"
    textColor: "{colors.drafting-ink}"
    rounded: "{rounded.hairline}"
    padding: "7px 13px"
  button-hover:
    backgroundColor: "{colors.drafting-film}"
  button-primary:
    backgroundColor: "{colors.drafting-ink}"
    textColor: "{colors.on-ink}"
    rounded: "{rounded.hairline}"
    padding: "7px 13px"
  button-primary-hover:
    backgroundColor: "#33393F"
  segmented-option-selected:
    backgroundColor: "{colors.suggestion-blue}"
    textColor: "{colors.on-ink}"
    padding: "7px 12px"
  field:
    backgroundColor: "{colors.sheet-white}"
    textColor: "{colors.drafting-ink}"
    rounded: "{rounded.hairline}"
    padding: "4px 6px"
  top-bar:
    backgroundColor: "{colors.drafting-ink}"
    textColor: "{colors.on-ink}"
    height: "56px"
    padding: "0 24px"
  delta-rule:
    backgroundColor: "{colors.markup-red}"
    textColor: "{colors.on-ink}"
    typography: "{typography.numeral}"
    width: "26px"
    height: "23px"
  delta-question:
    backgroundColor: "{colors.hold-amber}"
    textColor: "{colors.on-ink}"
    width: "26px"
    height: "23px"
  delta-ai:
    backgroundColor: "{colors.suggestion-blue}"
    textColor: "{colors.on-ink}"
    width: "26px"
    height: "23px"
  delta-confirmed:
    backgroundColor: "{colors.confirmed-green}"
    textColor: "{colors.on-ink}"
    width: "26px"
    height: "23px"
  finding-row-selected:
    backgroundColor: "{colors.markup-red-wash}"
    padding: "11px 8px 11px 4px"
  finding-row-ai-selected:
    backgroundColor: "{colors.suggestion-blue-wash}"
  evidence-sheet:
    backgroundColor: "{colors.drafting-film}"
    padding: "18px 20px 14px"
  answer-sheet:
    backgroundColor: "{colors.sheet-white}"
    padding: "28px 32px"
  hold-note:
    backgroundColor: "{colors.hold-amber-wash}"
    textColor: "#6E470C"
    padding: "10px 12px"
---

# Design System: RightFit

## Overview

**Creative North Star: "The Drawing Under Review"**

The page reads like an engineering drawing that a checker has marked up. The ground is drafting film, the frame is a single dark ink, and everything is held together by 1px hairlines instead of boxes and fills. Every finding is a numbered revision delta, the small triangle a checker draws beside a change, and the quote it rests on in the evidence is enclosed in a hand-drawn revision cloud. The same number appears in the finding list, on the cloud and in the answer, so the reviewer can follow one item across the whole review.

Density is that of a working document: three columns, compact tables, 13px reference text, and no decorative space. Color is not decoration. Each hue is a markup pen with one meaning, and the absence of color is the default state. Lettering is DIN, condensed and uppercase, the way a title block is lettered; anything meant to be read as a sentence is set in the system sans.

The world deliberately refuses the dashboard: there are no status pills, KPI tiles, card grids or gradient fills. The status is a single letter in a heavy frame, and the counts are bare numerals over plain labels.

**Key Characteristics:**
- Drafting-film ground, ink top bar, white sheet only where a document or the selected finding sits.
- Hierarchy by line weight: hairline, 1px ink, 2px ink, then the 5px status frame.
- Four markup colors with fixed meanings: red rules, blue AI, green confirmed, amber on hold.
- Triangular revision deltas and scalloped revision clouds are the only non-rectangular forms.
- DIN lettering for labels, headings and numbers; system sans for reading.

## Colors

One near-black ink on warm-white film, with four markup pens that each mean exactly one thing.

### Primary
- **Drafting Ink** (drafting-ink): The top bar, the primary button, heavy rules under the status and the table heads, the selected tab underline, and all main text. It is the frame of the page.

### Secondary
- **Markup Red** (markup-red): Deltas and revision clouds for findings the deterministic rules raised; the active package tab underline; the text caret. **Markup Red Ink** (markup-red-ink) is its text form, for "Problem" labels. **Markup Red Wash** (markup-red-wash) fills the selected finding row and the error box.

### Tertiary
- **Suggestion Blue** (suggestion-blue): Deltas, clouds and the selected decision for AI suggestions, and the focus ring. **Suggestion Blue Ink** (suggestion-blue-ink) is every link and the AI group heading. **Suggestion Blue Wash** (suggestion-blue-wash) fills a selected AI row.
- **Confirmed Green** (confirmed-green): A finding a person marked as not a problem, a ticked reading, the checkbox accent, and the A status frame. **Confirmed Green Wash** (confirmed-green-wash) fills staged readings and the dismissed note.
- **Hold Amber** (hold-amber): Questions that wait on a confirmation or the contractor, the B status frame, and the hold line under the status. **Hold Amber Wash** (hold-amber-wash) fills the hold note in the detail panel.

### Neutral
- **Drafting Film** (drafting-film): The page ground and the evidence strip.
- **Sheet White** (sheet-white): The detail panel, the answer letter, buttons and fields; it marks "a document" against the film.
- **Ink Secondary** (ink-secondary): Supporting text, column heads, descriptions.
- **Ink Tertiary** (ink-tertiary): The quietest text: document kinds, inactive tabs, tags.
- **Hairline** (hairline): Every 1px divider between rows, columns and list items.
- **On Ink / On Ink Secondary** (on-ink, on-ink-secondary): Text on the top bar, active and inactive.

### Named Rules
**The Markup Code Rule.** Red means the rules found it, blue means the AI suggests it, green means a person confirmed it, amber means it still waits on someone. A markup color never appears without that meaning, and a meaning never appears in another color.

**The One Ink Rule.** Hierarchy comes from line weight in the one ink (1px hairline, 1px ink, 2px ink, 5px status frame), not from extra greys, tinted panels or fills.

## Typography

**Display Font:** DIN Condensed (with Bahnschrift Condensed, Bahnschrift, Arial Narrow)
**Body Font:** System sans (-apple-system, Segoe UI, system-ui)
**Label/Mono Font:** DIN Alternate for numerals, with tabular figures

**Character:** Title-block lettering against plain reading text. The condensed DIN is always uppercase and lightly tracked; the sans stays in sentence case and does the explaining.

### Hierarchy
- **Display** (400, 104px, 0.8): The single status letter (A, B or C) inside its colored frame. One per page. 72px on phones.
- **Headline** (400, 44px, 1, uppercase): The status phrase beside the letter, such as "Approved as noted". 30px on phones.
- **Title** (400, 22–26px, 1.05, uppercase): The selected finding's heading (26px), the package heading in the rail and the answer letter head (22px).
- **Title Small** (400, 15–18px, 1, uppercase): Step tabs, group headings, the attachment list heading, the evidence heading. The "DRAFT · NOT SIGNED" stamp uses the same lettering at 17px in a 1.5px frame.
- **Body** (400, 15px, 1.45): Finding comments and evidence quotes, held to 62ch in the detail panel and 70–78ch for lead text and the answer.
- **Body Small** (400–600, 13–14px, 1.3–1.35): Table cells, row descriptions, file names, notes. Finding names in rows are 600 weight at 14px.
- **Label** (400, 12–13px, 0.04em, uppercase): Table column heads, fact labels, decision tags.
- **Numeral** (400, 24px, 1.1, tabular): Counts under the status; the same face at 11–15px for page references, values, sources and delta numbers.

### Named Rules
**The Lettering Rule.** Labels, headings and numbers are lettered in DIN; anything read as a sentence is set in the sans. Never set a paragraph in DIN or a column head in the sans.

**The Tabular Figures Rule.** Every number that can be compared (counts, pages, values, references) uses DIN Alternate with tabular figures.

## Layout

A full-height three-column desk below a 56px sticky top bar: a 300px attachments rail, a fluid centre for the status and the revision table, and a 440px detail panel on white. Columns are separated by 1px hairlines and each scrolls on its own. The centre has 22px top and 28px side padding; rail and panel use 18–24px.

Finding rows are a four-column grid (34px delta, fluid finding, 190px product, 112px source) with a 12px gap and hairline bottoms; the table top is a 1px ink rule. The status block ends with a 2px ink rule, and so do the notes and the sticky save bar. Spacing moves in small steps (4, 8, 12, 16, 22, 28px) and is tight by design.

Responsive behavior: at 1280px the bar drops the package meta. At 1240px the layout becomes two columns (260px rail) and the detail panel turns into a 460px sheet that slides in from the right. At 760px the bar grows to 100px and wraps the package tabs onto their own line, the rail hides behind a toggle, rows collapse to two columns, and the table heads disappear.

## Elevation & Depth

The drawing is flat. Depth comes from the film/white contrast and from line weight, not shadow. Only two things float above the drawing and cast a shadow: the toast and the sliding detail sheet on narrower screens. The current attachment is marked with a 1px inset ink outline, not a lift.

### Shadow Vocabulary
- **Toast** (`box-shadow: 0 8px 24px rgba(29, 33, 37, .22)`): The short confirmation message at the bottom centre.
- **Sliding sheet** (`box-shadow: -12px 0 40px rgba(29, 33, 37, .16)`): The detail panel when it overlays the page below 1240px.
- **Current outline** (`box-shadow: inset 0 0 0 1px #1D2125`): The selected attachment in the rail.

### Named Rules
**The Flat Sheet Rule.** Nothing that lies on the drawing casts a shadow. A shadow means the element floats over the page and will go away.

## Shapes

Rectangles with square or barely softened corners (2px on buttons, fields, segmented controls and the toast; 0 everywhere else). Borders are the main form device: hairlines between things, 1.5px ink around controls and the draft stamp, 5px around the status letter in the status color. Two shapes break the rectangle, and both come from drawing practice: the revision delta, an upward triangle cut with a clip path, and the revision cloud, a closed path of 10px-radius scallops drawn around the quoted evidence.

**The Square Corner Rule.** Corners stay at 2px or less. The triangle and the cloud are the only non-rectangular forms, and they are reserved for findings.

## Components

### Buttons
Plain drafting-office controls: outlined, square, quiet.
- **Shape:** Nearly square (2px), with a 1.5px ink border.
- **Default:** White fill, ink text, 14px sans, 7px 13px padding, optional 16px line icon with a 1.6 stroke.
- **Primary:** Ink fill with white text; one per action group ("Mark as not a problem", "Copy the answer").
- **Hover / Focus:** Default hover shifts to the film color; primary hover lightens slightly. Focus is a 2px blue outline offset by 2px, everywhere.
- **Disabled:** 45% opacity.
- **Link button:** Blue ink text with a 1px underline offset 3px, no box; used for "Cancel", file references and "Open the PDF".

### Segmented decision
The AI decision control: options sit side by side inside one 1.5px ink frame, separated by 1px ink lines. The chosen option fills with Suggestion Blue and white text; others hover to the blue wash. It is blue because it decides on AI output.

### Inputs / Fields
- **Style:** White fill, 1px mid-grey border (#A9ACA6), 2px corners, 13px text in the rail; the reason box uses a 1.5px ink border and 64px minimum height.
- **Focus:** The shared 2px blue outline; the caret is red.
- **Hover:** Border darkens to ink.

### Navigation
- **Package tabs:** In the ink bar, 14px sans in the secondary on-ink color; the current package turns white and gets a 3px red underline.
- **Step tabs:** DIN 18px uppercase, numbered ("1 · Findings 6"), with a tabular count; the selected tab gets a 3px ink underline sitting on the 1px ink rule. Long labels drop on phones.

### Revision delta (signature)
A filled upward triangle carrying the finding number in white tabular DIN. Red for a rule finding, amber for a question, blue for an AI suggestion (numbered A1, A2 until accepted), green and empty for one marked not a problem. Three sizes: 20px in the rail markers, 26px in rows and the answer, 46px at the head of the detail panel. The number is the same wherever the finding appears.

### Revision cloud (signature)
The evidence quote sits on a strip of drafting film with a hairline border, and a scalloped cloud is drawn around it in a 2px red stroke (blue for AI evidence), with the finding's delta pinned to its top-right corner. On selection the cloud draws itself along its length over 0.7s with the long-tail ease, staggered 140ms per cloud; with reduced motion it simply appears.

### Finding rows
Full-width buttons in the revision table: delta, name and two-line description, product, source. Hover adds a faint ink tint; the selected row fills with the red wash (blue wash for AI rows). A finding marked not a problem or an AI suggestion rejected is struck through, not hidden.

### Status block
The status letter in a 5px frame (green A, amber B, red C) beside the uppercase status phrase, a row of bare numeral counts with plain labels, an expandable "Why" with a drawn chevron, and an amber hold line. It closes with a 2px ink rule.

### Attachment list
Numbered rows (DIN number, file name, kind and pages) with an extent bar: a 3px ink line whose length is the document's page count against the longest one. Small deltas on the right show which findings point at that document.

### Answer letter
A white sheet with a hairline border, up to 78ch wide, a DIN head, numbered lines each led by its delta, and a sign-off under a 2px ink rule.

### Notes
Hold and dismissed notes are flat wash blocks (amber, green) with a darker text ink of the same hue (#6E470C, #1F5535) and 10px 12px padding. Errors use a 1.5px red border on the red wash.

## Do's and Don'ts

### Do:
- **Do** give every finding one number and show that same number on its delta in the list, on its cloud and in the answer.
- **Do** keep each markup color to its one meaning: red rules, blue AI, green confirmed by a person, amber waiting.
- **Do** separate content with 1px hairlines and step up to 1px or 2px ink for structure, before reaching for any fill.
- **Do** letter labels, headings and numbers in uppercase DIN, and set sentences in the system sans.
- **Do** use tabular DIN numerals for counts, pages, values and references.
- **Do** keep corners at 2px or square.
- **Do** strike through dismissed or rejected findings so the decision stays visible.

### Don't:
- **Don't** add status pills, KPI tiles or card grids; status is the framed letter and counts are bare numerals.
- **Don't** use a markup color for decoration, branding or emphasis without its meaning.
- **Don't** put shadows on anything that lies on the drawing; only the toast and the sliding sheet float.
- **Don't** use the triangle or the cloud for anything other than findings and their evidence.
- **Don't** set body text in DIN or column heads in the sans.
