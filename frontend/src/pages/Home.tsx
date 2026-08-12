import { useQuery } from '@tanstack/react-query'
import { type CSSProperties, useState } from 'react'
import { Link } from 'react-router-dom'
import { Quatrefoil, SearchIcon } from '../components/icons'
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

/*
 * The mascot for this screen lives in the AppShell header (it lounges on
 * the header's own rule); its boots reach ~20px below the frieze, which
 * `main`'s py-7 already clears — no extra spacing needed here.
 */
export function Home() {
  const [search, setSearch] = useState('')
  const { data, isPending, isError } = useQuery({
    queryKey: ['recipes'],
    queryFn: fetchRecipes,
  })

  if (isPending) {
    return (
      <div className="flex flex-col items-center gap-4 pt-12">
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
    )
  }

  if (isError) {
    return (
      <div className="tile tile-keyline px-5 py-6 text-center">
        <p className="font-display font-bold text-ink">
          Não foi possível carregar as receitas. Tente novamente.
        </p>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 pt-10 text-center">
        <Quatrefoil className="h-14 w-14 text-tile" />
        <p className="font-display text-xl font-extrabold tracking-tight text-ink">
          Nenhuma receita salva ainda.
        </p>
        <p className="max-w-[15rem] text-sm text-ink-muted">
          Cole o link de uma receita na aba Adicionar para começar.
        </p>
      </div>
    )
  }

  // Client-side only — the whole library is already in cache, so filtering
  // it locally is instant and needs no round trip to the backend.
  const query = search.trim().toLowerCase()
  const visibleRecipes =
    query === '' ? data : data.filter((recipe) => recipe.title.toLowerCase().includes(query))

  return (
    <section className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between border-b-2 border-ink pb-2">
        <h2 className="font-display text-sm font-extrabold uppercase tracking-[0.2em] text-ink">
          Receitário
        </h2>
        <span className="font-display text-sm font-bold text-accent">
          {data.length.toString().padStart(2, '0')}
        </span>
      </div>

      <div className="relative">
        <label htmlFor="recipe-search" className="sr-only">
          Pesquisar receitas
        </label>
        <SearchIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-muted" />
        <input
          id="recipe-search"
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar por título…"
          className="field w-full py-2.5 pr-4 pl-9 text-sm"
        />
      </div>

      {visibleRecipes.length === 0 ? (
        <p className="pt-4 text-center text-sm text-ink-muted">
          Nenhuma receita encontrada para &quot;{search.trim()}&quot;.
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {visibleRecipes.map((recipe, index) => {
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
      )}
    </section>
  )
}
