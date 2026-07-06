// Mosaic treemap of `chart_data.theme_treemap`. 1:1 port of TARGET
// redesign/treemap-variants.jsx::ThemeTreemapMosaic + sliceAndDice +
// TreemapHoverCard + BaselineCaption (lines 6-475).
//
// Squarified layout keeps areas comparable without the long-strip illusion.
//
// Why absolute-positioned DIVs (not SVG <rect>): SVG `text` with
// preserveAspectRatio="none" stretches the typography horizontally when
// the container aspect doesn't match the viewBox. DIV tiles keep text
// natural at every container width. The ResizeObserver measures the
// container so the layout re-runs on resize.
//
// HoverCard glides between adjacent tiles via translate3d + cubic-bezier
// — never remounts, so the transition is physical, not snappy.

import { useEffect, useMemo, useRef, useState } from "react"
import { ArrowRight } from "lucide-react"

import { getS } from "@/lib/i18n"
import type { ThemeTreemap, ThemeTreemapNode } from "@/lib/types"

export interface TopicsTreemapProps {
  data?: ThemeTreemap | null
  height?: number
  /** Called with the first paper_id in the clicked tile's cluster. */
  onSelect?: (paperId: string) => void
}

interface RankedTheme extends ThemeTreemapNode {
  rank: number
}

interface Tile extends RankedTheme {
  x: number
  y: number
  w: number
  h: number
}

interface AreaItem {
  theme: RankedTheme
  area: number
}

const EASING_POP = "cubic-bezier(0.16, 1, 0.3, 1)"
const EASING_STD = "cubic-bezier(0.4, 0, 0.2, 1)"
const MIN_LABEL_TILE_HEIGHT = 36
const MIN_READABLE_SIDE = 56
const RECT_EPSILON = 0.5

function labelLineCount(height: number, fontSize: number) {
  const available = Math.max(12, height)
  const lineHeight = fontSize * 1.18
  return Math.max(1, Math.min(4, Math.floor(available / lineHeight)))
}

function tilePadding(tiny: boolean, compact: boolean) {
  if (tiny) return { x: 5, y: 4 }
  if (compact) return { x: 9, y: 7 }
  return { x: 13, y: 10 }
}

function tileLabelFontSize(w: number, h: number) {
  if (w <= 74 || h <= 34) return 10
  if (w <= 132 || h <= 58) return 11.5
  return 13
}

function tileMetricFontSize(w: number, h: number) {
  if (w <= 132 || h <= 58) return 10.5
  return 12
}

function canShowMetric(w: number, h: number) {
  return w >= 70 && h >= 38
}

function isTinyTile(w: number, h: number) {
  return w <= 64 || h <= 30
}

function isCompactTile(w: number, h: number) {
  return w <= 132 || h <= 58
}

function tileContentHeight(h: number, paddingY: number) {
  return Math.max(8, h - paddingY * 2)
}

function metricBottom(paddingY: number) {
  return Math.max(3, paddingY - 1)
}

function metricLeft(paddingX: number) {
  return paddingX
}

function metricRight(paddingX: number) {
  return paddingX
}

function labelMaxHeight(h: number, paddingY: number, showMetric: boolean) {
  const contentH = tileContentHeight(h, paddingY)
  return showMetric ? Math.max(12, contentH - 18) : contentH
}

function metricTextValue(value: number, pct: number) {
  return `${value} · ${pct}%`
}

function labelTextValue(rank: number, name: string) {
  return `#${rank} ${name}`
}

function tileTextColors(lightText: boolean) {
  return {
    textColor: lightText ? "hsl(var(--background))" : "hsl(var(--foreground))",
    metricColor: lightText
      ? "hsl(var(--background))"
      : "hsl(var(--foreground))",
  }
}

function useFullLabelStyle(w: number, h: number, showMetric: boolean) {
  return !showMetric && w >= 160 && h >= MIN_LABEL_TILE_HEIGHT
}

function worstRatio(row: AreaItem[], side: number) {
  if (row.length === 0 || side <= 0) return Infinity
  const sum = row.reduce((s, t) => s + t.area, 0)
  const min = Math.min(...row.map((t) => t.area))
  const max = Math.max(...row.map((t) => t.area))
  const side2 = side * side
  return Math.max((side2 * max) / (sum * sum), (sum * sum) / (side2 * min))
}

function layoutRow(
  row: AreaItem[],
  rect: { x: number; y: number; w: number; h: number },
) {
  const area = row.reduce((s, t) => s + t.area, 0)
  const tiles: Tile[] = []
  if (rect.w >= rect.h) {
    const colW = area / rect.h
    let nextY = rect.y
    row.forEach((item, index) => {
      const tileH =
        index === row.length - 1 ? rect.y + rect.h - nextY : item.area / colW
      tiles.push({ ...item.theme, x: rect.x, y: nextY, w: colW, h: tileH })
      nextY += tileH
    })
    return {
      tiles,
      rect: { x: rect.x + colW, y: rect.y, w: rect.w - colW, h: rect.h },
    }
  }

  const rowH = area / rect.w
  let nextX = rect.x
  row.forEach((item, index) => {
    const tileW =
      index === row.length - 1 ? rect.x + rect.w - nextX : item.area / rowH
    tiles.push({ ...item.theme, x: nextX, y: rect.y, w: tileW, h: rowH })
    nextX += tileW
  })
  return {
    tiles,
    rect: { x: rect.x, y: rect.y + rowH, w: rect.w, h: rect.h - rowH },
  }
}

function projectedMinSide(
  row: AreaItem[],
  rect: { w: number; h: number },
) {
  const area = row.reduce((s, t) => s + t.area, 0)
  if (rect.w >= rect.h) {
    const colW = area / rect.h
    return Math.min(colW, ...row.map((t) => t.area / colW))
  }

  const rowH = area / rect.w
  return Math.min(rowH, ...row.map((t) => t.area / rowH))
}

function squarifyTreemap(
  items: RankedTheme[],
  x: number,
  y: number,
  w: number,
  h: number,
): Tile[] {
  const total = items.reduce((s, t) => s + t.value, 0)
  if (total <= 0 || w <= 0 || h <= 0) return []

  const scale = (w * h) / total
  const remaining = items.map((theme) => ({ theme, area: theme.value * scale }))
  const tiles: Tile[] = []
  let rect = { x, y, w, h }
  let row: AreaItem[] = []

  while (remaining.length > 0) {
    const next = remaining[0]
    const side = Math.min(rect.w, rect.h)
    const candidate = [...row, next]
    // ponytail: small guard beats owning a chart lib just to keep tail labels readable.
    const wouldPinchTail =
      row.length > 0 && projectedMinSide(candidate, rect) < MIN_READABLE_SIDE
    const isLastTailItem = remaining.length === 1
    if (
      row.length === 0 ||
      isLastTailItem ||
      (!wouldPinchTail && worstRatio(candidate, side) <= worstRatio(row, side))
    ) {
      row.push(next)
      remaining.shift()
    } else {
      const laid = layoutRow(row, rect)
      tiles.push(...laid.tiles)
      rect = laid.rect
      row = []
    }
  }
  if (row.length > 0) tiles.push(...layoutRow(row, rect).tiles)
  return tiles
}

function sameColumn(a: Tile, b: Tile) {
  return Math.abs(a.x - b.x) <= RECT_EPSILON && Math.abs(a.w - b.w) <= RECT_EPSILON
}

function touchesAbove(above: Tile, below: Tile) {
  return sameColumn(above, below) && Math.abs(above.y + above.h - below.y) <= RECT_EPSILON
}

function rebalanceTinyTailTiles(tiles: Tile[]) {
  const adjusted = tiles.map((tile) => ({ ...tile }))
  const tailFirst = [...adjusted].sort((a, b) => b.rank - a.rank)

  for (const tile of tailFirst) {
    if (tile.h >= MIN_LABEL_TILE_HEIGHT) continue

    const aboveTiles = adjusted
      .filter((candidate) => candidate.rank < tile.rank && sameColumn(candidate, tile))
      .sort((a, b) => b.y - a.y)
    const nearest = aboveTiles.find((candidate) => touchesAbove(candidate, tile))
    if (!nearest) continue

    const donors: Tile[] = []
    let cursor = tile
    for (const candidate of aboveTiles) {
      if (!touchesAbove(candidate, cursor) || candidate.value !== nearest.value) break
      donors.unshift(candidate)
      cursor = candidate
    }
    if (donors.length === 0) continue

    const needed = MIN_LABEL_TILE_HEIGHT - tile.h
    const capacity = donors.reduce(
      (sum, donor) => sum + Math.max(0, donor.h - MIN_READABLE_SIDE),
      0,
    )
    const borrowed = Math.min(needed, capacity)
    if (borrowed <= 0) continue

    const top = donors[0].y
    const bottom = tile.y + tile.h
    const donorTotal = donors.reduce((sum, donor) => sum + donor.h, 0)
    const newDonorTotal = donorTotal - borrowed
    const newTileH = tile.h + borrowed
    let nextY = top

    donors.forEach((donor, index) => {
      const donorH =
        index === donors.length - 1
          ? bottom - newTileH - nextY
          : (donor.h / donorTotal) * newDonorTotal
      donor.y = nextY
      donor.h = donorH
      nextY += donorH
    })
    tile.y = bottom - newTileH
    tile.h = newTileH
  }

  return adjusted
}

export function TopicsTreemap({ data, height = 420, onSelect }: TopicsTreemapProps) {
  const [hover, setHover] = useState<Tile | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(1100)

  useEffect(() => {
    if (!containerRef.current) return
    const update = () => {
      setWidth(containerRef.current?.offsetWidth || 1100)
    }
    update()
    const obs = new ResizeObserver(update)
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  const themes = useMemo<RankedTheme[]>(() => {
    const raw = (data?.themes || []) as ThemeTreemapNode[]
    return raw
      .filter((t) => typeof t.value === "number" && t.value > 0)
      .sort((a, b) => (b.value as number) - (a.value as number))
      .map((t, i) => ({ ...t, rank: i + 1 }))
  }, [data])

  if (themes.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height,
          fontSize: 12,
          color: "hsl(var(--muted-foreground))",
          border: "1px dashed hsl(var(--border))",
          borderRadius: "var(--radius)",
          fontFamily: "var(--font-sans)",
        }}
      >
        {getS().topicNotAvailable ||
          "Topic clustering not available for this run."}
      </div>
    )
  }

  const tiles = rebalanceTinyTailTiles(
    squarifyTreemap(themes, 0, 0, width, height),
  )
  const total = themes.reduce((s, t) => s + t.value, 0)
  const maxValue = themes[0]?.value ?? 0
  const minValue = themes[themes.length - 1]?.value ?? maxValue
  const alphaFor = (value: number) =>
    maxValue === minValue
      ? 0.7
      : 0.32 + ((value - minValue) / (maxValue - minValue)) * 0.6

  return (
    <div>
      <div
        ref={containerRef}
        style={{
          position: "relative",
          width: "100%",
          height,
          borderRadius: 6,
          background: "hsl(var(--muted) / 0.4)",
          overflow: "hidden",
        }}
      >
        {tiles.map((t) => {
          const isHover = hover && hover.name === t.name
          const alpha = alphaFor(t.value)
          const lightText = alpha > 0.55
          const pct = Math.round((t.value / total) * 100)
          const fill = `hsl(var(--chart-1) / ${
            isHover ? Math.min(1, alpha + 0.06) : alpha
          })`
          const paperIds = (t.paper_ids || []) as string[]
          const clickable = !!(onSelect && paperIds.length > 0)
          const showMetric = canShowMetric(t.w, t.h)
          const fullLabelStyle = useFullLabelStyle(t.w, t.h, showMetric)
          const compact = !fullLabelStyle && isCompactTile(t.w, t.h)
          const tiny = isTinyTile(t.w, t.h)
          const metricText = metricTextValue(t.value, pct)
          const labelText = labelTextValue(t.rank, t.name)
          const padding = tilePadding(tiny, compact)
          const labelFontSize = tileLabelFontSize(t.w, t.h)
          const labelHeight = labelMaxHeight(t.h, padding.y, showMetric)
          const labelLineClamp = labelLineCount(
            labelHeight,
            labelFontSize,
          )
          const { textColor, metricColor } = tileTextColors(lightText)

          return (
            <div
              key={t.name}
              onMouseEnter={() => setHover(t)}
              onMouseLeave={() => setHover(null)}
              onClick={
                clickable ? () => onSelect?.(paperIds[0]) : undefined
              }
              style={{
                position: "absolute",
                left: t.x,
                top: t.y,
                width: t.w,
                height: t.h,
                boxSizing: "border-box",
                background: fill,
                cursor: clickable ? "pointer" : "default",
                transition: `background .3s ${EASING_STD}, box-shadow .2s ${EASING_STD}`,
                boxShadow: isHover
                  ? "inset 0 0 0 2px hsl(var(--background)), inset 0 0 0 3.2px hsl(var(--foreground) / 0.55)"
                  : "inset 0 0 0 2px hsl(var(--background))",
                padding: `${padding.y}px ${padding.x}px`,
                overflow: "hidden",
                willChange: "background, box-shadow",
              }}
              title={t.name}
            >
              {isHover && (
                <div
                  style={{
                    position: "absolute",
                    inset: 2,
                    boxShadow: "inset 0 0 0 1.2px hsl(var(--foreground))",
                    pointerEvents: "none",
                    animation: `rd-treemap-tile-in .18s ${EASING_POP}`,
                  }}
                />
              )}
              <div
                style={{
                  fontSize: labelFontSize,
                  fontWeight: 600,
                  letterSpacing: 0,
                  color: textColor,
                  lineHeight: tiny ? 1.1 : compact ? 1.16 : 1.2,
                  maxHeight: labelHeight,
                  overflow: "hidden",
                  display: "-webkit-box",
                  WebkitLineClamp: labelLineClamp,
                  WebkitBoxOrient: "vertical",
                  overflowWrap: "anywhere",
                  wordBreak: "break-word",
                  fontFamily: "var(--font-sans)",
                }}
              >
                {labelText}
              </div>
              {showMetric && (
                <div
                  style={{
                    position: "absolute",
                    left: metricLeft(padding.x),
                    right: metricRight(padding.x),
                    bottom: metricBottom(padding.y),
                    fontFamily: "var(--font-mono)",
                    fontSize: tileMetricFontSize(t.w, t.h),
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: 600,
                    color: metricColor,
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    textOverflow: "clip",
                  }}
                >
                  {metricText}
                </div>
              )}
            </div>
          )
        })}
        {hover && (
          <TreemapHoverCard
            hover={hover}
            total={total}
            onSelect={onSelect}
            container={{ w: width, h: height }}
          />
        )}
      </div>
      <BaselineCaption themes={themes} total={total} />
    </div>
  )
}

interface HoverCardProps {
  hover: Tile
  total: number
  onSelect?: (paperId: string) => void
  container: { w: number; h: number }
}

function TreemapHoverCard({
  hover,
  total,
  onSelect,
  container,
}: HoverCardProps) {
  const S = getS()
  // Edge-clamped placement: prefer right of anchor; fall back to left;
  // then above; then below. Always keep an 8px gap from container edges.
  const CARD_W = Math.max(160, Math.min(320, container.w - 16))
  const titleLines = Math.max(1, Math.ceil(Array.from(hover.name).length / 16))
  const CARD_H = Math.min(
    Math.max(120, container.h - 16),
    Math.max(132, 112 + Math.min(4, titleLines - 1) * 18),
  )
  const GAP = 8
  const clampX = (value: number) =>
    Math.min(Math.max(8, value), Math.max(8, container.w - CARD_W - 8))
  const clampY = (value: number) =>
    Math.min(Math.max(8, value), Math.max(8, container.h - CARD_H - 8))
  let pos = { x: 0, y: 0 }
  if (hover.x + hover.w + GAP + CARD_W <= container.w) {
    pos = {
      x: hover.x + hover.w + GAP,
      y: clampY(hover.y),
    }
  } else if (hover.x - GAP - CARD_W >= 0) {
    pos = {
      x: hover.x - GAP - CARD_W,
      y: clampY(hover.y),
    }
  } else {
    const above = hover.y - GAP - CARD_H >= 0
    pos = above
      ? {
          x: clampX(hover.x),
          y: hover.y - GAP - CARD_H,
        }
      : {
          x: clampX(hover.x),
          y: clampY(hover.y + hover.h + GAP),
        }
  }

  const paperIds = (hover.paper_ids || []) as string[]
  const pct = Math.round((hover.value / total) * 100)

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
        width: CARD_W,
        maxHeight: Math.max(120, container.h - 16),
        boxSizing: "border-box",
        padding: "12px 14px",
        background: "hsl(var(--popover))",
        color: "hsl(var(--popover-foreground))",
        boxShadow:
          "0 10px 32px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.04), 0 0 0 1px hsl(var(--border))",
        borderRadius: 8,
        fontSize: 12,
        lineHeight: 1.5,
        pointerEvents: "none",
        transition: `transform .28s ${EASING_POP}`,
        willChange: "transform",
        animation: `rd-treemap-card-in .18s ${EASING_POP} both`,
        fontFamily: "var(--font-sans)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
          marginBottom: 10,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontFamily: "var(--font-mono)",
            fontWeight: 500,
            letterSpacing: "0.06em",
            padding: "2px 6px",
            borderRadius: 4,
            background: "hsl(var(--muted))",
            color: "hsl(var(--muted-foreground))",
          }}
        >
          #{hover.rank}
        </span>
        <span
          style={{
            fontWeight: 600,
            color: "hsl(var(--foreground))",
            letterSpacing: 0,
            minWidth: 0,
            flex: 1,
            overflowWrap: "anywhere",
            wordBreak: "break-word",
            whiteSpace: "normal",
            lineHeight: 1.35,
          }}
        >
          {hover.name}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          fontFamily: "var(--font-mono)",
          fontVariantNumeric: "tabular-nums",
          color: "hsl(var(--muted-foreground))",
        }}
      >
        <span
          style={{
            color: "hsl(var(--foreground))",
            fontWeight: 600,
            fontSize: 22,
            letterSpacing: "-0.015em",
            lineHeight: 1,
          }}
        >
          {hover.value}
        </span>
        <span style={{ fontSize: 11 }}>{S.papers || "papers"}</span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span style={{ fontSize: 11 }}>{pct}%</span>
      </div>
      <div
        style={{
          marginTop: 10,
          height: 3,
          background: "hsl(var(--muted))",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "hsl(var(--foreground))",
            transition: `width .32s ${EASING_POP}`,
          }}
        />
      </div>
      {paperIds.length > 0 && onSelect && (
        <div
          style={{
            marginTop: 12,
            paddingTop: 10,
            borderTop: "1px solid hsl(var(--border))",
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: "hsl(var(--muted-foreground))",
          }}
        >
          <span>{S.openTopPaper || "Open top paper"}</span>
          <ArrowRight size={11} strokeWidth={1.75} />
        </div>
      )}
    </div>
  )
}

interface BaselineCaptionProps {
  themes: RankedTheme[]
  total: number
}

function BaselineCaption({ themes, total }: BaselineCaptionProps) {
  const largest = themes[0]
  const largestPct = Math.round((largest.value / total) * 100)
  const S = getS()
  return (
    <div
      style={{
        marginTop: 14,
        paddingTop: 12,
        borderTop: "1px solid hsl(var(--border))",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        gap: 12,
        fontSize: 11.5,
        color: "hsl(var(--muted-foreground))",
        fontFamily: "var(--font-sans)",
      }}
    >
      <span>
        <span
          className="tabular"
          style={{
            fontFamily: "var(--font-mono)",
            color: "hsl(var(--foreground))",
            fontWeight: 600,
          }}
        >
          {total}
        </span>
        <span style={{ margin: "0 6px" }}>{S.papersAcross || "papers across"}</span>
        <span
          className="tabular"
          style={{
            fontFamily: "var(--font-mono)",
            color: "hsl(var(--foreground))",
            fontWeight: 600,
          }}
        >
          {themes.length}
        </span>
        <span style={{ marginLeft: 4 }}>{S.topics || "topics"}</span>
      </span>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10.5,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
        }}
      >
        {S.largest || "Largest"}:{" "}
        <span style={{ color: "hsl(var(--foreground))", fontWeight: 600 }}>
          {largest.name}
        </span>
        <span style={{ marginLeft: 6 }}>{largestPct}%</span>
      </span>
    </div>
  )
}
