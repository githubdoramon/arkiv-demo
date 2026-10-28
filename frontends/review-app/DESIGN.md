---
name: Sidequest
description: A charcoal and citron game collection led by real cover artwork.
colors:
  bg: "#0c0d0e"
  surface: "#17191c"
  surface-alt: "#202326"
  ink: "#f5f6f0"
  muted: "#aeb2b4"
  line: "#35393c"
  accent: "#e5fa36"
  accent-soft: "#30371c"
  action-ink: "#131607"
  field-bg: "#1b1d1e"
  field-line: "#3c4141"
  editor-bg: "#1b1f20"
  editor-line: "#677334"
  danger: "#f1aaa2"
  danger-bg: "#382729"
  ambient-teal: "#29596788"
  ambient-gold: "#81723055"
  ambient-night: "#111c26"
  ambient-ink: "#101219"
  ambient-green: "#171c1b"
  ambient-citron: "#6f86302c"
  ambient-indigo: "#36477460"
  action-highlight: "#f0ff79"
  action-shade: "#d3eb28"
  action-glow: "#ffffffe6"
  action-sheen: "#ffffffa0"
typography:
  display:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "clamp(42px, 4.6vw, 70px)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0em"
  title:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    lineHeight: 1.85
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "13px"
    lineHeight: 1.5
rounded:
  field: "10px"
  surface: "12px"
  compact-cover: "8px"
  panel: "14px"
  pill: "20px"
  circle: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "18px"
  gutter-mobile: "20px"
  lg: "25px"
  panel: "30px"
  grid-row: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.field}"
    padding: "14px 23px"
  button-secondary:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "9px 14px"
  input-search:
    backgroundColor: "{colors.field-bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "10px 10px 10px 43px"
    height: "46px"
  platform-selected:
    backgroundColor: "{colors.accent}"
    textColor: "#111608"
    rounded: "{rounded.surface}"
    padding: "7px 12px"
  review-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "30px"
  editor-panel:
    backgroundColor: "{colors.editor-bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "30px"
---

# Design System: Sidequest

## Overview

**Creative North Star: "The Console Collection"**

Charcoal chrome gives real game covers the foreground. Citron marks the current selection and the next useful action; condensed titles give games a confident voice while precise sans-serif controls stay quiet. This is the implemented world selected through Sidequest B.

Browsing is image-led and compact. Reading and writing use calm, legible panels. Source links and account details stay secondary to player activity, with “Sign in” as the account entry point. Artwork supplies the variety; the surrounding interface stays consistent.

**Key Characteristics:**

- Real portrait covers and selected-game atmosphere.
- Charcoal surfaces with focused citron actions.
- Condensed game headings and practical sans-serif controls.
- Short selection feedback with reduced-motion support.

## Colors

The palette pairs a dark neutral foundation with a single vivid accent. Frontmatter values are normative and map to the current stylesheet.

### Primary

- **Citron** (`accent`): primary actions, selected platforms, selection outlines, ratings and keyboard focus.
- **Olive shadow** (`accent-soft`): quiet account prompts and status marks.
- **Action ink** (`action-ink`): dark text against citron buttons.

### Neutral

- **Console charcoal** (`bg`): the page and surrounding chrome.
- **Raised charcoal** (`surface`, `surface-alt`): review panels, controls and secondary actions.
- **Warm chalk** (`ink`): primary text; **silver grey** (`muted`): supporting metadata.
- **Graphite rule** (`line`): separators and control edges.
- **Field charcoal** (`field-bg`, `field-line`): the library's search and filter controls.
- **Editor charcoal and olive edge** (`editor-bg`, `editor-line`): the active writing surface.
- **Error rose** (`danger`, `danger-bg`): inherited error-status colors, separate from brand emphasis.

**The Artwork Leads Rule.** Let real game imagery supply the broad color variation; reserve citron for interaction, selection and review signals.

## Typography

**Display Font:** Barlow Condensed Bold, with sans-serif fallback.
**Body Font:** DM Sans, with sans-serif fallback.

Both families are self-hosted with `font-display: swap`; DM Sans is variable, while the condensed face is the supplied bold weight. Font sources and OFL licenses are in `../../shared/public/fonts/` relative to this app.

- **Display:** selected-game name, uppercase and balanced, with the frontmatter's fluid scale. The detail heading uses `clamp(38px, 5vw, 64px)` at a unit line-height.
- **Headline:** collection title; editor and review-toolbar headings use the same condensed family at (32px).
- **Title:** catalog game names use the compact sans-serif role. Artwork lettering remains part of the publisher image.
- **Body:** review prose preserves line breaks, wraps long content and stops at (70ch). Game summaries use smaller sans-serif text and do not replace review prose.
- **Label:** form labels use the shared role; compact metadata varies by context. Do not reuse tiny metadata sizes for primary reading or controls.

**The Two Voices Rule.** Use condensed type for game and section headings; use DM Sans for actions, forms, account information and reviews.

## Layout

The desktop header uses percentage side gutters (3.1%) and an (88px) minimum height. Search, genre and platform filters sit beside navigation when space permits and wrap into a separate row at (1250px).

The library's four-cover selector is centered within (1350px), with (25px) gaps and (42px) side padding. The selected-game strip below it has a (1400px) maximum width. The catalog uses seven columns with (32px) row and (18px) column gaps; it becomes eight columns from (1700px), five at or below (1250px), four at or below (800px), and two at or below (540px).

At (540px) and below, use (20px) page gutters. The featured covers become a native horizontal scroll gallery with (44vw) columns and scroll snapping; only the gallery should scroll horizontally. Filters use a full-width search above two selects. The selected title and action share a row, followed by compact genre metadata.

Detail pages have a (1250px) maximum width. Review cards use an author column and a reading column, becoming one column at (800px). Editors use two columns with (25px) gaps and collapse at (540px); the primary action becomes full-width. Mobile panels use (22px 18px) padding. Keep real covers proportional at (2:3) with explicit `height: auto` where the image is not filling a fixed cover box.

## Elevation & Depth

Depth is selective: atmospheric artwork fades into charcoal, covers sit above it, and the selected cover uses a citron outline and a small scale change. Review surfaces rely on tone rather than shadows. The account popover and floating feedback use soft dark shadows; avoid spreading this elevation to ordinary panels.

### Shadow Vocabulary

- **Gallery cover:** `0 20px 35px #0006`.
- **Detail cover:** `0 12px 30px #0006`.
- **Account popover:** `0 16px 64px #0009`.
- **Floating feedback:** `0 14px 50px #05060c80`.

Motion is brief: ordinary controls transition over (160ms), covers select over (250ms), and the backdrop arrives over (280ms). Pointer-only cover lifts and button sheen are gated to fine hover devices. Reduced motion stops transitions and ambient drift while retaining static card tilt. The gallery and information row reserve stable dimensions across selections; long titles wrap within their own grid cell. Slow teal, olive and indigo light fields extend behind the full collection (26s/32s drift). Primary actions use a citron gradient, persistent inner hover light, a 750ms sheen and a tactile pressed inset. The backdrop gradients support artwork legibility; the half-star gradient communicates a partial rating.

## Shapes

Rounded rectangular covers and panels define the system. Desktop featured covers and review cards share the surface radius; compact covers use the smaller radius on mobile. Actions and search controls use the field radius. Popovers and the detail hero use the panel radius. Initial avatars and small cover-action buttons are circular. Dividers are thin and quiet.

## Components

### Buttons

Primary buttons are citron, dark-text actions with a (48px) minimum height, bold sans-serif labels and optional inline SVG icons. The selection-strip action has more vertical padding (17px 24px). Pressing scales to (.97); fine-pointer hover runs the sheen and shifts the arrow (3px). Secondary actions use `surface-alt`, a thin line border and compact padding. Disabled states lower opacity. Preserve the shared (2px) accent focus outline with (3px) offset.

### Inputs / Fields

Library fields have a dark fill, quiet border and a (46px) height, reducing to (42px) on small screens. The search icon is an inline SVG positioned inside left padding. Select arrows are CSS strokes. Editors use visibly associated labels, generous textarea line-height and vertical resizing. Focus uses the same accent outline as buttons.

### Chips

Platform buttons are compact rounded rectangles with a thin border and a dark translucent resting fill. Selection changes fill and border to citron with dark text. Static platform labels in the selection strip are quieter; do not make them look like the primary action.

### Cards / Containers

Catalog items are open button compositions: cover, name, year and review summary, without an extra enclosing panel. Fine-pointer hover lifts the cover (4px); keyboard focus reveals its circular arrow too. Review cards use `surface` with the panel spacing, real review text and secondary metadata. Active review/profile editors use the olive border, preserving their distinction from published content.

### Navigation

The compact Sidequest mark and uppercase sans-serif wordmark lead. “Discover” has a citron underline; “Reviewers” links to Afterword. “Sign in” is the clear account action; signed-in controls expose the player profile and sign-out. Only local development on the local network exposes the native account chooser. All production builds open the browser sign-in request directly. On mobile navigation and filters wrap into separate rows.

### Featured cover selector

Four real covers are selection buttons with `aria-pressed` and descriptive accessible names. Selecting a cover updates the title, summary, platforms, genres and artwork backdrop. The selected cover scales to (1.035) on desktop and (1.04) on mobile, with a (2px) outline. Keep labels and actions as HTML; never ship raster comp text as interactive UI.

## Do's and Don'ts

### Do:

- **Do** keep real publisher cover art proportional and use the catalog's actual platform labels.
- **Do** use “Sign in,” “My profile” and “View source” in ordinary player flows.
- **Do** preserve keyboard focus, reduced motion and native mobile gallery scrolling.
- **Do** use real reviews, feedback and reputation values throughout.
- **Do** use inline SVG for interface icons and preserve accessible text labels.

### Don't:

- **Don't** replace publisher artwork with generated art or ship controls that appeared only in a comp.
- **Don't** apply cover-hover movement to reading or writing surfaces.
- **Don't** turn optional account addresses and technical implementation details into the main player-facing message.
- **Don't** import Afterword's paper, serif headings or editorial columns as Sidequest defaults.

Primary button hover and press timings use three times the original duration at the user’s request: 480ms transform, 600ms shadow, 540ms inner-light opacity and 750ms light movement/sheen. The arrow transition is 480ms. Reduced-motion behavior remains in place.
