import { t } from "@/lib/i18n"
import type { ActualQueryGroup } from "@/lib/types"

export interface ActualQueryStripProps {
  groups?: ActualQueryGroup[]
}

export function ActualQueryStrip({ groups }: ActualQueryStripProps) {
  const visibleGroups = (groups ?? []).filter(
    (group) => group.source && group.queries?.length,
  )

  if (visibleGroups.length === 0) return null

  return (
    <div className="psp-query-strip" aria-label={t("actualSearchQueries")}>
      <div className="psp-query-strip-kicker">{t("actualSearchQueries")}</div>
      <div className="psp-query-strip-grid">
        {visibleGroups.map((group) => (
          <div className="psp-query-strip-row" key={group.source}>
            <span className="psp-query-strip-source">{group.source}</span>
            <span className="psp-query-strip-chips">
              {(group.queries ?? []).map((query) => (
                <span className="psp-query-strip-chip" key={query}>
                  {query}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
