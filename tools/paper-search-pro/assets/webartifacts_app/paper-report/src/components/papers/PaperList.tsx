// Paper list — groups papers by tier, renders TierHeader + a stack of rows
// (or cards when view === 'card'). Peripheral tier is collapsed by default.
// Direct port of TARGET redesign/app-2-papers.jsx (297-371).

import * as React from "react"
import { Info } from "lucide-react"

import type { NormalizedPaper, Tier } from "@/lib/types"
import { TIER_ORDER } from "@/lib/format"
import { t } from "@/lib/i18n"

import { TierHeader } from "./TierHeader"
import { PaperCardItem } from "./PaperCardItem"
import { PaperRowCatalog } from "./PaperRowCatalog"

export interface PaperRowComponentProps {
  paper: NormalizedPaper
  index: number
  onSelect: (paper: NormalizedPaper) => void
  dim?: boolean
}

export type PaperRowComponent = (props: PaperRowComponentProps) => React.ReactElement

export interface PaperListProps {
  papers: NormalizedPaper[]
  /** 'compact' | 'card' (matches FilterBar values) */
  view: string
  /** RCS threshold on 0-10 scale (matches FilterBar slider) */
  threshold: number
  search: string
  onSelect: (paper: NormalizedPaper) => void
  /** Override the default row component (e.g. PaperRowIndex). Default: PaperRowCatalog */
  RowComponent?: PaperRowComponent
}

export function PaperList({
  papers,
  view,
  threshold,
  search,
  onSelect,
  RowComponent,
}: PaperListProps) {
  const Row: PaperRowComponent = RowComponent || PaperRowCatalog

  // NOTE (2026-05-23): previous "recommended" focus filter removed — it forced
  // a Foundational+High-only view with no UI to disable, so clicking
  // Moderate/Emerging/Peripheral in TierStrip produced an empty list. See
  // App.tsx ReportShell comment for the full rationale.
  const tierFilter =
    threshold > 0
      ? papers.filter((p) => p.rcsValid && p.rcs >= threshold)
      : papers
  const searched = search
    ? tierFilter.filter((p) => {
        const q = search.toLowerCase()
        return (
          (p.title || "").toLowerCase().includes(q) ||
          (p.tldr || "").toLowerCase().includes(q) ||
          (p.abstract || "").toLowerCase().includes(q) ||
          (p.authorsFull || []).some((a) => a.toLowerCase().includes(q)) ||
          (p.venue || "").toLowerCase().includes(q)
        )
      })
    : tierFilter

  const validScored = searched.filter((p) => p.rcsValid)
  const unscored = searched.filter((p) => !p.rcsValid)

  // Group by tier. Invalid scaffold/parser-fallback values are listed in a
  // separate unavailable section so a neutral raw `rcs=5` never masquerades as
  // an Emerging tier.
  const groups: Partial<Record<Tier, NormalizedPaper[]>> = {}
  for (const p of validScored) {
    if (!groups[p.tier]) groups[p.tier] = []
    groups[p.tier]!.push(p)
  }

  // Peripheral collapsed by default
  const [collapsed, setCollapsed] = React.useState<Partial<Record<Tier, boolean>>>({
    Peripheral: true,
  })
  function toggleTier(t: Tier) {
    setCollapsed((c) => ({ ...c, [t]: !c[t] }))
  }

  let globalIdx = 0

  return (
    <div style={{ maxWidth: 1240, margin: "0 auto", padding: "0 40px 80px" }}>
      {searched.length === 0 && (
        <div
          style={{
            padding: 56,
            textAlign: "center",
            border: "1px dashed hsl(var(--border))",
            borderRadius: "var(--radius)",
            color: "hsl(var(--muted-foreground))",
            marginTop: 32,
          }}
        >
          <Info style={{ width: 20, height: 20, display: "inline-block" }} />
          <p style={{ margin: "8px 0 0", fontSize: 13 }}>{t("noPapersMatch")}</p>
        </div>
      )}

      {TIER_ORDER.map((tier) => {
        const items = groups[tier]
        if (!items || items.length === 0) return null
        const isCollapsed = !!collapsed[tier]
        return (
          <section key={tier}>
            <TierHeader
              tier={tier}
              count={items.length}
              collapsed={isCollapsed}
              onToggle={() => toggleTier(tier)}
            />
            {!isCollapsed && (
              <div
                style={
                  view === "card"
                    ? {
                        display: "flex",
                        flexDirection: "column",
                        gap: 14,
                        padding: "8px 0 0",
                      }
                    : undefined
                }
              >
                {items.map((p) => {
                  const idx = globalIdx++
                  return view === "card" ? (
                    <PaperCardItem
                      key={p.id}
                      paper={p}
                      index={idx}
                      onSelect={onSelect}
                    />
                  ) : (
                    <Row
                      key={p.id}
                      paper={p}
                      index={idx}
                      onSelect={onSelect}
                      dim={false}
                    />
                  )
                })}
              </div>
            )}
          </section>
        )
      })}

      {unscored.length > 0 && (
        <section>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              padding: "30px 4px 12px",
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 500,
                fontFamily: "var(--font-mono)",
                textTransform: "uppercase",
                letterSpacing: "0.14em",
                color: "hsl(var(--foreground))",
              }}
            >
              {t("rcsUnavailableTitle")}
            </span>
            <span
              className="tabular"
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "hsl(var(--muted-foreground))",
                opacity: 0.7,
              }}
            >
              {unscored.length}
            </span>
            <div
              style={{
                flex: 1,
                height: 1,
                background: "hsl(var(--border))",
                margin: "0 4px",
              }}
            />
            <span
              style={{
                fontSize: 11,
                color: "hsl(var(--muted-foreground))",
                fontFamily: "var(--font-mono)",
              }}
            >
              {t("rcsUnavailableReason")}
            </span>
          </div>
          <div
            style={
              view === "card"
                ? {
                    display: "flex",
                    flexDirection: "column",
                    gap: 14,
                    padding: "8px 0 0",
                  }
                : undefined
            }
          >
            {unscored.map((p) => {
              const idx = globalIdx++
              return view === "card" ? (
                <PaperCardItem
                  key={p.id}
                  paper={p}
                  index={idx}
                  onSelect={onSelect}
                />
              ) : (
                <Row
                  key={p.id}
                  paper={p}
                  index={idx}
                  onSelect={onSelect}
                  dim={true}
                />
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
