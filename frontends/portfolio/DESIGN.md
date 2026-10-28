---
name: Afterword
description: An open editorial home for a reviewer's voice and game collection.
colors:
  bg: "#fafaf8"
  surface: "#fff"
  surface-alt: "#efefeb"
  ink: "#111b28"
  muted: "#576172"
  line: "#d0d3d5"
  accent: "#b33326"
  accent-soft: "#f5e7e1"
  control-line: "#a4acb4"
  structural-line: "#969fa8"
  danger: "#982d21"
  danger-bg: "#f8e7e2"
  paper-warm: "#e4c8b9d0"
  paper-cool: "#c9d6e4c0"
  paper-ground: "#f8f3ee"
  paper-shadow: "#eef2f4"
  paper-rose: "#b3332612"
  paper-inkwash: "#b3c3ce45"
  reading-wash: "#fafaf880"
  search-wash: "#ffffff70"
typography:
  display:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "clamp(52px, 5.8vw, 88px)"
    fontWeight: 400
    lineHeight: 1.03
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "clamp(26px, 2.7vw, 40px)"
    fontWeight: 400
    lineHeight: 1.13
    letterSpacing: "-0.025em"
  title:
    fontFamily: "DM Serif Display, Georgia, serif"
    fontSize: "31px"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Georgia, Times New Roman, serif"
    fontSize: "19px"
    lineHeight: 1.6
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "13px"
    lineHeight: 1.5
rounded:
  control: "4px"
  square: "0px"
  circle: "50%"
spacing:
  xs: "10px"
  sm: "15px"
  md: "20px"
  mobile-gutter: "20px"
  lg: "25px"
  column: "30px"
  section: "40px"
components:
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.control}"
    padding: "10px 0 10px 10px"
  input-search:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "11px 12px 11px 40px"
    height: "48px"
  profile-link:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  profile-link-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  reviewer-monogram:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.circle}"
    size: "75px"
  review-cover:
    rounded: "{rounded.square}"
    width: "180px"
---

# Design System: Afterword

## Overview

**Creative North Star: "The Critic's Column"**

Afterword gives the reviewer a light editorial home. Deep ink, an expressive serif and vermilion details establish an identity independent from Sidequest. Thin rules and open columns create structure without enclosing every piece of writing in a card. This is the implemented world selected through Afterword A.

The author's perspective leads; real game covers act as reading anchors. Serif review prose carries the voice, while a quiet sans-serif handles dates, platforms, feedback and links. Public account details remain available without competing with the name, bio and writing.

**Key Characteristics:**

- Near-white paper, deep ink and restrained vermilion.
- Expressive serif headings, readable serif prose and sans-serif metadata.
- Open editorial columns separated by thin rules.
- Real portrait cover inserts and circular initials.

## Colors

The light neutral palette leaves space for the writing and publisher images; vermilion supplies a restrained editorial accent. Frontmatter values are normative and map to the current stylesheet.

### Primary

- **Editorial vermilion** (`accent`): the masthead stroke, initials, ratings, selected navigation and primary reading links.
- **Blush paper** (`accent-soft`): directory initials and quiet status backgrounds.

### Neutral

- **Reading paper** (`bg`): the main canvas; **white** (`surface`): floating feedback.
- **Soft paper** (`surface-alt`): inherited secondary surfaces.
- **Deep ink** (`ink`): headings, prose and the directory search action.
- **Slate** (`muted`): navigation support, dates, platforms and feedback metadata.
- **Pale rule** (`line`): columns and review separators; **structural rule** (`structural-line`): masthead and footer; **control rule** (`control-line`): fields and outlined links.
- **Error vermilion** (`danger`, `danger-bg`): recoverable error feedback, separate from ordinary accent use.

**The Quiet Accent Rule.** Use vermilion for identity, ratings and useful link emphasis; let ink and paper carry the reading surface.

## Typography

**Display Font:** DM Serif Display, with Georgia and serif fallbacks.
**Body Font:** Georgia, then Times New Roman and serif, for review prose.
**Label Font:** DM Sans, with sans-serif fallback, for controls and metadata.

DM Serif Display and variable DM Sans are self-hosted with `font-display: swap`; sources and OFL licenses are in `../../shared/public/fonts/` relative to this app. Georgia is the implemented reading face, not the display identity.

- **Display:** the author's name uses the fluid frontmatter scale. The directory opening uses `clamp(50px, 6.2vw, 86px)` with the same line-height and tracking. The masthead is (52px) on desktop.
- **Headline:** game titles introduce each review; use balanced wrapping rather than forcing short titles onto a fixed line count.
- **Title:** directory names use the smaller display role; the compact review index uses a serif (18px) title.
- **Body:** review prose preserves original line breaks and wraps long content within (65ch). It grows to (21px) above (1650px) and is (19px) with a (1.65) line-height on small screens. Author bios use sans-serif text.
- **Label:** controls and supporting content use DM Sans. Platform/date lines and feedback counts are compact metadata, never the reading body.

**The Author's Voice Rule.** Let expressive serif headings and stable serif prose lead; keep interaction labels and record metadata in the quieter sans-serif voice.

## Layout

The outer shell has percentage gutters (3%) and a (1720px) maximum width. The masthead is a horizontal row with a (100px) minimum height and a thin bottom rule. The profile has three columns: author rail (235px), flexible reading column and review index (225px), with (30px) gaps. The rail and index remain sticky on desktop; only the central column has vertical rules and (35px 30px 40px) padding.

Each review is an open row with a proportional (2:3) cover, a (180px) cover column and a (25px) gap. At (1650px) and above, outer columns and cover inserts increase slightly. At (1200px) and below, the review index disappears and the author rail narrows. At (800px) and below, shell gutters are (25px), the rail and cover inserts become more compact, and the directory opening becomes one column.

At (560px) and below, use (20px) gutters and a wrapped masthead. The author rail becomes a compact opening block with initials, bio, horizontal statistics and links. The reading column loses its side borders. Each review starts with a (92px) cover beside its title and rating, then puts prose across the full width below. Keep the (19px) mobile reading text and generous line-height.

The directory uses a (1300px) maximum width, an open two-column introduction and ruled reviewer rows. Each row combines initials, a real bio and up to three real review covers. At the smallest breakpoint the covers sit below the identity, keeping their own proportions. Review and reputation counts always come from actual records.

## Elevation & Depth

The editorial surface uses warm-paper and cool-ink light fields at the edges. Slow 34s/40s drift gives the background movement while the reading column stays still; reduced motion holds these fields static. Paper, whitespace and thin rules establish hierarchy. Covers and ordinary review rows have no shadows. Floating feedback is the exception, using `0 16px 48px #17213020` on white. The inherited technical explorer remains a utility surface, not a model for editorial pages.

**The Open Page Rule.** Keep reviews and directory entries open on the canvas; use rules and spacing for separation before introducing enclosing panels.

Links use short (150–180ms) color or underline transitions. A directory row may move its arrow (5px) and first cover slightly on fine-pointer hover. The reading column stays still. Refresh rotation runs only when reduced motion is not requested; reduced motion removes animations, transitions and decorative transforms.

## Shapes

Controls use a small, functional corner radius. Review cover inserts and index thumbnails are square-cornered rectangles at (2:3). Initials are circular, with a vermilion fill in the author rail and a blush fill in the directory. The wordmark's short vermilion underline is part of the Afterword identity. Do not carry Sidequest's rounded console panels into this system.

## Components

### Buttons

Directory search filters immediately while typing and has no submit button; Enter can still open a unique match. Refresh is a quiet icon-and-label action with no panel fill. Shared focus uses a (2px) vermilion outline with (3px) offset. Disabled controls lower opacity. Avoid turning every reading link into a filled button.

### Inputs / Fields

The directory search field has a translucent white wash with the control rule, a (48px) height and an inset inline SVG search icon. The accessible label supports reviewer names and optional account-address entry; the visible placeholder remains “Find a reviewer.” Focus uses the shared accent outline.

### Navigation

The serif Afterword masthead leads, with a short vermilion stroke beneath. “Reviewers” returns to the directory; “Explore games” links to Sidequest. Refresh sits at the far right. Active navigation uses the accent, while ordinary links remain ink. Navigation wraps below the masthead at the smallest breakpoint.

### Cards / Containers

Reviewer rows and review articles are open, ruled compositions, not boxed cards. Directory rows are full links with visible identity and a supporting cover cluster. Review articles preserve real prose and pair it with platform, date, rating, feedback and source links. There are no chip/tag components in the editorial reading surface; metadata stays plain text.

### Profile links

Desktop author links have a thin outline and small rounded corners, reversing to ink on hover. On mobile they become plain compact links and use vermilion hover feedback. Review links use a short partial underline that extends on hover or keyboard focus; “Read on Sidequest” is the accent action and “View source” remains secondary.

### Author rail and review index

The author rail holds circular initials, real bio, review/reputation/helpful-vote counts and useful profile links. Optional account details use a disclosure. The review index is a compact navigational list with cover, game title, platform and rating; its uppercase list heading is a functional navigation label, not a decorative eyebrow pattern.

## Do's and Don'ts

### Do:

- **Do** preserve real reviewer names, bios, prose, platform labels and reputation values.
- **Do** use self-hosted DM Serif Display for identity and Georgia for the implemented reading body.
- **Do** keep cover images proportional, square-cornered and sourced from the real catalog.
- **Do** preserve generous mobile reading text, keyboard focus and reduced-motion behavior.
- **Do** keep source links and optional account details available in a secondary role.

### Don't:

- **Don't** import Sidequest's dark surfaces, citron actions or condensed display type.
- **Don't** turn open review rows into a stack of elevated cards.
- **Don't** animate the reading column or make the prose move during ordinary reading.
- **Don't** copy invented comp prose, counts or a generated portrait into the product.
- **Don't** make technical account terminology the main promise of the reviewer page.
