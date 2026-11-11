---
name: RightFit
description: A material approval review drawn as the approval form in triplicate, where the ink says whether a person has confirmed a value.
colors:
  bottle-green: "#0E3B2E"
  bottle-green-hover: "#1B5A47"
  form-ground: "#E7F0E8"
  band: "#DCE9DF"
  rail-soft: "#B7D1C0"
  sheet: "#FFFFFF"
  line: "#C5D6CA"
  line-soft: "#E5EDE7"
  rule: "#B9CDBF"
  ink: "#15191A"
  ink-2: "#3D4A42"
  label: "#4A5D51"
  carbon: "#4A32B8"
  carbon-wash: "#F4F2FF"
  carbon-line: "#DAD5F2"
  problem-red: "#C4311E"
  problem-wash: "#FBEDEA"
  question-ochre: "#8A5A00"
  question-wash: "#FAF1DF"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    letterSpacing: "-0.015em"
  answer:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "21px"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    letterSpacing: "-0.01em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "14.5px"
    fontWeight: 400
    lineHeight: 1.42
    fontFeature: "\"tnum\""
  small:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.07em"
  typed-value:
    fontFamily: "Courier, \"Courier New\", monospace"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  typed-figure:
    fontFamily: "Courier, \"Courier New\", monospace"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  answer-letter:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 800
    lineHeight: "44px"
rounded:
  sm: "3px"
  md: "4px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  row: "14px"
  gutter-narrow: "16px"
  gap: "18px"
  gutter: "26px"
components:
  button-primary:
    backgroundColor: "{colors.bottle-green}"
    textColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  button-primary-hover:
    backgroundColor: "{colors.bottle-green-hover}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.bottle-green}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  button-secondary-hover:
    backgroundColor: "{colors.band}"
  button-mini:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.bottle-green}"
    rounded: "{rounded.sm}"
    height: "28px"
    padding: "0 7px"
  decision-control:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.carbon}"
    rounded: "{rounded.md}"
    padding: "9px 12px"
  decision-control-chosen:
    backgroundColor: "{colors.carbon}"
    textColor: "{colors.sheet}"
  field:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "7px 9px"
  rail:
    backgroundColor: "{colors.bottle-green}"
    textColor: "{colors.band}"
    width: "196px"
  rail-link-current:
    backgroundColor: "{colors.form-ground}"
    textColor: "{colors.bottle-green}"
    rounded: "{rounded.md}"
    padding: "8px 10px"
  answer-letter-a:
    backgroundColor: "{colors.bottle-green}"
    textColor: "{colors.sheet}"
    typography: "{typography.answer-letter}"
    rounded: "{rounded.md}"
    width: "44px"
  answer-letter-return:
    backgroundColor: "{colors.problem-red}"
    textColor: "{colors.sheet}"
    typography: "{typography.answer-letter}"
    rounded: "{rounded.md}"
    width: "44px"
  chip-fail:
    backgroundColor: "{colors.problem-wash}"
    textColor: "{colors.problem-red}"
    rounded: "{rounded.sm}"
    padding: "3px 7px"
  chip-pass:
    backgroundColor: "{colors.band}"
    textColor: "{colors.bottle-green}"
    rounded: "{rounded.sm}"
    padding: "3px 7px"
  hold-note:
    backgroundColor: "{colors.carbon-wash}"
    padding: "9px 14px"
  question-note:
    backgroundColor: "{colors.question-wash}"
    textColor: "{colors.question-ochre}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
---

# Design System: RightFit

## Overview

**Creative North Star: "The Approval Form in Triplicate"**

The whole application is drawn as the paper form an engineer fills in, signs and files in copies. A bottle-green rail holds the navigation; the work sits on a pale form-green ground; every working surface is a plain white sheet with a thin green-grey border and no rounded card corners. Labels are printed: small capitals, wide tracking, quiet grey-green. Values are typed: bold Courier, the way a form filled on a typewriter looks. The page of the real document sits beside the work at a fixed scale, with the quoted lines marked on it.

The system is built around one distinction: who wrote a value. What the AI read and nobody has confirmed is carbon violet with a dashed underline, like a carbon copy. Once a person confirms it, it becomes black with a solid underline, and the change is drawn as ink running from left to right, on the sheet and on the page at the same time. Every other color is held to one job: red for problems, ochre for questions, bottle green for what you can press or follow.

Density is that of a working form: 14.5px body, tight rows, tabular figures, no decoration. Depth comes from borders and tinted bands, not from shadows.

**Key Characteristics:**
- Bottle-green rail, form-green ground, white sheets with thin borders.
- Printed labels in small capitals; values typed in bold Courier.
- Carbon violet dashed for unconfirmed AI readings, black solid once a person confirms.
- Red, ochre and green each keep a single meaning.
- System faces only; no font files ship.

## Colors

A cool green paper palette with one violet ink for machine readings and two signal colors held to single meanings.

### Primary
- **Bottle Green** (bottle-green): the rail, every button, links, navigation, the selection frame around the open problem and the active tab underline. Also the progress ticks for decided items and the "A" answer letter and passing chips.
- **Bottle Green, Lifted** (bottle-green-hover): hover on the rail links and on primary buttons only.

### Secondary
- **Carbon Violet** (carbon): only what the AI read and nobody confirmed, the AI tags on problem rows, the "your decision" control, the focus ring, text selection and the text cursor. On the document page its 17% tint fills the marked lines.
- **Carbon Wash** (carbon-wash) and **Carbon Rule** (carbon-line): the note above the problem list that says what is still on hold.

### Tertiary
- **Problem Red** (problem-red): problems only. Failing chips, the "return" answer banner, figures that fail a check, error text, and the B and C draft-answer letters. **Problem Wash** (problem-wash) backs the failing chip.
- **Question Ochre** (question-ochre): questions only. The "Question" tag on a row and the notice that a page is a scan. **Question Wash** (question-wash) backs that notice.

### Neutral
- **Form Ground** (form-ground): the page behind every sheet, and the current rail link.
- **Band** (band): group headers in the problem list, table headers, the passed section, button hover; also the text color of the rail.
- **Rail Soft** (rail-soft): the rail's group label and footnote.
- **Sheet** (sheet): every working surface, fields and secondary buttons.
- **Line** (line), **Line Soft** (line-soft), **Rule** (rule): sheet borders, row separators inside a sheet, and the field and tab-bar strokes, in that order of weight.
- **Ink** (ink): body text and confirmed values; also the toast and the progress fill.
- **Ink 2** (ink-2): secondary sentences, notes and captions.
- **Label** (label): printed labels, table headers and small metadata.

### Named Rules
**The Carbon Copy Rule.** Carbon violet with a dashed underline (1.5px on text, 2px on the page mark) means the AI read it and no person has confirmed it. Nothing else may be violet and dashed together. Once a person confirms, the value turns ink black with a solid underline.

**The One Meaning Rule.** Red is only for problems and the draft-answer letter. Ochre is only for questions. Bottle green is only for links, selection frames, buttons and navigation. A color never borrows another's job.

## Typography

**Body Font:** the system sans (-apple-system, SF Pro Text, Helvetica Neue, Arial)
**Typed Font:** Courier, then Courier New, then the system monospace

**Character:** a printed form with typewritten entries. The sans does every heading, label and sentence; Courier appears only where a value has been entered, so the eye can tell a field's name from its content at a glance. Both are the system's own faces: the project owner decided on 11 Nov 2026 not to ship self-hosted fonts.

### Hierarchy
- **Headline** (700, 24px, -0.015em): the title of a screen.
- **Answer** (700, 21px, line-height 1.15): the draft answer beside its letter in the package head; the answer banner uses 22px.
- **Title** (700, 18px, -0.01em): the open problem, the document card and the answer letter sheet.
- **Body** (400, 14.5px, line-height 1.42, tabular figures): all running text.
- **Small** (400, 13.5px; 13px for captions, 12.5px for row metadata): notes, tags, page links.
- **Label** (500, 11px, 0.07em, uppercase): the printed field label above or beside a typed value, and table column heads.
- **Typed value** (Courier 700, 16px, -0.01em): a value read from the documents; 13px inside group headers, 22px and 30px for the large figures on the tool screens.
- **Answer letter** (sans 800, 30px in a 44px square; 16px in a 26px square when small): the draft-answer letter.

### Named Rules
**The Typed Value Rule.** Courier bold is reserved for values entered on the form: readings, model names, figures. Labels, sentences and controls are never typed.

## Layout

The application is a two-column grid: a 196px rail and the main area, which scrolls on its own while the window stays fixed. Screens pad 22px top and 26px at the sides and stop at 1320px.

The package review is three stacked bands: a head row (form number, package, answer letter, ticks for what remains), a tab bar (1 Problems, 2 Confirm readings, 3 Answer), and the work area. The work area splits into the problem sheet on the left and the document sheet on the right (54%), 18px apart. Rows inside sheets pad 14px at the sides and 7 to 9px vertically. The document page renders at up to 640px wide, centered on a faintly green scroll area.

Responsive behavior:
- **Up to 1100px:** the rail turns into a horizontal bar across the top, the work split becomes 5 to 7, gutters drop to 16px, the tool screens stack to one column. Between 761 and 1100px the document page renders at a fixed 640px width (the sheet scrolls sideways if needed) and the decision buttons stay pinned at the bottom of the open problem.
- **Up to 760px:** the whole page scrolls as one, the problem sheet and the document stack, the page fills the width, field labels move above their values, and the packages table hides its secondary columns.

Reduced motion shortens every animation to nothing and removes transitions.

## Elevation & Depth

The system is flat. Sheets are separated from the ground by a 1px line and from each other by tinted bands, never by shadow. Only three things lift: the document page, which carries a hairline ring and a faint green shadow so it reads as paper; and the two things that float over the work, the "why" popover and the toast.

### Shadow Vocabulary
- **Paper** (`box-shadow: 0 0 0 1px #DDE5DF, 0 2px 8px rgba(14, 59, 46, .08)`): the rendered document page only.
- **Float** (`box-shadow: 0 8px 24px rgba(14, 59, 46, .18)`): the popover that explains the draft answer.
- **Toast** (`box-shadow: 0 8px 24px rgba(14, 59, 46, .28)`): the confirmation toast at the bottom.
- **Selection frame** (`box-shadow: inset 0 0 0 1.5px` bottle green): the open problem and the current page group; a frame, not a lift.

### Named Rules
**The Flat Sheet Rule.** Working surfaces never cast shadows. Only the document page and things that float over the work may.

## Shapes

Square paper with barely softened controls. Sheets, tables and file rows have square corners. Controls take a 4px radius (buttons, fields, the decision control, notes, the answer letter, the banner); small things take 3px (page buttons, chips, the small letter). Checkboxes are 15px squares with a 2px radius. Strokes are 1px for sheet borders and separators and 1.5px for controls and for the ink underlines. The only round shape is the loading spinner. Icons are 16px line drawings on a 20-unit grid, 1.8px stroke, round caps and joins, drawn in the current text color.

## Components

### Buttons
Plain, outlined, green.
- **Shape:** gently softened corners (4px), 1.5px bottle-green border, 600 weight, 10px by 14px padding, an optional 16px icon 7px from the text.
- **Primary:** bottle-green fill with white text; hover lifts to the lighter green.
- **Secondary:** white with green text and border; hover fills with the band color.
- **Mini:** the page-turn and zoom buttons beside the document, 28px tall, 1px rule border, 3px corners.
- **Link button:** green underlined text with no box, for secondary actions inside rows.
- **Disabled:** 45% opacity.

### Decision control
Keep, Not a problem and the other decisions on an open problem sit in one segmented control outlined in carbon violet, because the choice answers an AI suggestion. Unchosen segments are white with violet text; the chosen one fills violet with white text. It uses radio semantics.

### Chips and tags
- **Chips:** 12.5px, 600 weight, 3px corners. Failing: red on the problem wash. Passing: green on the band. Not applicable or unknown: label grey on a pale green-grey.
- **Row tags:** plain colored text at the end of a problem row: violet for AI suggestions, ochre for questions, grey for "Not a problem".

### Sheets and rows
- **Sheet:** white, 1px line border, square corners, no shadow.
- **Group header:** a full-width band with the product name in typed Courier and a count in small text.
- **Row:** checkbox, sentence and tag, 8px by 14px padding, a soft line above, a pale green hover. A dismissed row is struck through in label grey.
- **Open problem:** the selected row expands in place inside a 1.5px bottle-green frame on a pale green fill, showing its title, its sentence, its readings as label and typed value pairs, and its decision buttons.

### Fields
- **Style:** white, 1.5px rule border, 4px corners, 7px by 9px padding. Hover turns the border bottle green. Checkboxes use the green accent.
- **Focus:** every focusable element takes a 2px carbon-violet outline offset by 2px; on the rail the outline is white.

### Navigation
- **Rail:** 196px of bottle green, the product name in white 20px bold, links in band-colored text with 8px by 10px padding and 4px corners. Hover fills with the lighter green; the current link fills with the form ground and turns green and semi-bold. A small-capital group label separates the tools. Below 1100px it becomes a top bar.
- **Tabs:** numbered steps with 600 weight; the current tab gets a white fill and a 3px green underline.

### The Re-ink (signature)
Confirming a reading redraws it in ink: the black copy wipes across the violet one from left to right over 0.46s on the soft ease (cubic-bezier(.16, 1, .3, 1)), and the dashed underline becomes solid. The same mark on the document page fills from left to right over 0.36s when it appears, violet-tinted with a dashed bottom edge while unconfirmed and a faint grey with a solid black edge once confirmed.

### Answer letter and progress ticks
The draft answer is a single white letter on a filled square: green for A, red for B and C. Beside it, a row of 14 by 7px ticks shows each item: grey-green to do, green decided, black confirmed.

## Do's and Don'ts

### Do:
- **Do** show every value the AI read in carbon violet with a dashed underline until a person confirms it, and in ink black with a solid underline after.
- **Do** type values in bold Courier and print their labels in 11px small capitals with 0.07em tracking.
- **Do** keep working surfaces as white sheets with a 1px line border on the form-green ground.
- **Do** put the real document page beside the problem, with the quoted lines marked on it.
- **Do** use the system faces in the two stacks given; no font files ship.
- **Do** give every focusable element the 2px carbon-violet outline.

### Don't:
- **Don't** use red for anything but problems and the draft-answer letter, or ochre for anything but questions.
- **Don't** use bottle green for anything but links, selection frames, buttons and navigation.
- **Don't** put a violet dashed underline on anything a person has confirmed, or a black solid one on anything nobody has.
- **Don't** set labels, sentences or buttons in Courier.
- **Don't** add shadows to sheets, rows or buttons; only the document page and floating layers lift.
- **Don't** round sheets or tables; corners stay square, controls stay at 3 to 4px.
