import { useQuery } from '@tanstack/react-query'
import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { MascotHanging } from '../components/Mascot'
import { Quatrefoil } from '../components/icons'
import { fetchRecipes } from '../api/recipes'

function timeSummary(minutes: number | null): string | null {
  return minutes === null ? null : `${minutes} min`
}

/**
 * Tiles are stuck on the wall by hand, not laid by a machine: alternating
 * cards lean and shift a hair in opposite directions.
 */
function tileStyle(index: number): CSSProperties {
  const leansLeft = index % 2 === 0
  return {
    '--i': index,
    // `rotate` (not `transform`) so the press animation can translate the
    // tile without flattening its lean.
    rotate: leansLeft ? '-0.55deg' : '0.55deg',
    marginRight: leansLeft ? '0.5rem' : undefined,
    marginLeft: leansLeft ? undefined : '0.5rem',
  } as CSSProperties
}

/**
 * The mascot hangs off the header's rule and dangles over the list.
 *
 * It is anchored here rather than inside the sticky header on purpose: at
 * ~104px tall it would otherwise sit permanently over the tiles as they
 * scroll past. Parked in the page it grips the rule while the list is at
 * rest — which is when it is actually looked at — and then slides up
 * behind the header as you scroll.
 *
 * `-top-[37px]` reaches back through `main`'s padding and the frieze so the
 * mitts land on the dogtooth frieze just under the header — the rule they
 * appear to grip. They deliberately clear the header's own border: the
 * sticky header paints over anything above it, so mitts placed on that
 * border would be half-swallowed. `pt-[72px]` is the room its feet need.
 */
function MascotShelf({ children }: { children: ReactNode }) {
  return (
    <section className="relative pt-[72px]">
      <MascotHanging className="pointer-events-none absolute -top-[37px] right-0 w-[84px]" />
      {children}
    </section>
  )
}

export function Home() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['recipes'],
    queryFn: fetchRecipes,
  })

  if (isPending) {
    return (
      <MascotShelf>
        <div className="flex flex-col items-center gap-4 pt-6">
          <div className="flex gap-2" aria-hidden="true">
            {[0, 1, 2].map((index) => (
              <span
                key={index}
                className="tile-bob h-3 w-3 rounded-[2px] border-2 border-ink bg-accent"
                style={{ '--i': index } as CSSProperties}
              />
            ))}
          </div>
          <p className="font-display text-sm font-bold uppercase tracking-[0.18em] text-ink-muted">
            Carregando receitas…
          </p>
        </div>
      </MascotShelf>
    )
  }

  if (isError) {
    return (
      <MascotShelf>
        <div className="tile tile-keyline px-5 py-6 text-center">
          <p className="font-display font-bold text-ink">
            Não foi possível carregar as receitas. Tente novamente.
          </p>
        </div>
      </MascotShelf>
    )
  }

  if (data.length === 0) {
    return (
      <MascotShelf>
        <div className="flex flex-col items-center gap-3 pt-4 text-center">
          <Quatrefoil className="h-14 w-14 text-tile" />
          <p className="font-display text-xl font-extrabold tracking-tight text-ink">
            Nenhuma receita salva ainda.
          </p>
          <p className="max-w-[15rem] text-sm text-ink-muted">
            Cole o link de uma receita na aba Adicionar para começar.
          </p>
        </div>
      </MascotShelf>
    )
  }

  return (
    <MascotShelf>
      <div className="flex flex-col gap-5">
        <div className="flex items-baseline justify-between border-b-2 border-ink pb-2">
          <h2 className="font-display text-sm font-extrabold uppercase tracking-[0.2em] text-ink">
            Receitário
          </h2>
          <span className="font-display text-sm font-bold text-accent">
            {data.length.toString().padStart(2, '0')}
          </span>
        </div>

        <ul className="flex flex-col gap-4">
          {data.map((recipe, index) => {
            const facts = [
              recipe.servings !== null ? `${recipe.servings} porções` : null,
              timeSummary(recipe.total_time_minutes),
            ].filter((fact): fact is string => fact !== null)

            return (
              <li key={recipe.id}>
                <Link
                  to={`/recipes/${recipe.id}`}
                  style={tileStyle(index)}
                  className="tile tile-pressable tile-drop flex items-center gap-4 px-4 py-4"
                >
                  {/* Decorative only — keeps the link's accessible name equal
                      to the recipe title, which the tests pin down. */}
                  <span
                    aria-hidden="true"
                    className="shrink-0 font-display text-2xl font-extrabold tabular-nums text-accent"
                  >
                    {(index + 1).toString().padStart(2, '0')}
                  </span>
                  <span className="flex min-w-0 flex-col gap-1">
                    <span className="font-display text-lg leading-tight font-bold tracking-tight text-ink">
                      {recipe.title}
                    </span>
                    {facts.length > 0 && (
                      <span className="text-xs font-medium uppercase tracking-[0.1em] text-ink-muted">
                        {facts.join(' · ')}
                      </span>
                    )}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </div>
    </MascotShelf>
  )
}
