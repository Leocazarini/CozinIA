import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchRecipes } from '../api/recipes'

function timeSummary(minutes: number | null): string | null {
  return minutes === null ? null : `${minutes} min`
}

export function Home() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['recipes'],
    queryFn: fetchRecipes,
  })

  if (isPending) {
    return (
      <p className="pt-10 text-center font-display italic text-ink-muted">
        Carregando receitas…
      </p>
    )
  }

  if (isError) {
    return (
      <p className="pt-10 text-center text-ink-muted">
        Não foi possível carregar as receitas. Tente novamente.
      </p>
    )
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 pt-16 text-center">
        <p className="font-display text-xl italic text-ink-muted">
          Nenhuma receita salva ainda.
        </p>
        <p className="text-sm text-ink-muted">
          Cole o link de uma receita na aba Adicionar para começar.
        </p>
      </div>
    )
  }

  return (
    <ul className="flex flex-col gap-3">
      {data.map((recipe) => {
        const facts = [
          recipe.servings !== null ? `${recipe.servings} porções` : null,
          timeSummary(recipe.total_time_minutes),
        ].filter((fact): fact is string => fact !== null)

        return (
          <li key={recipe.id}>
            <Link
              to={`/recipes/${recipe.id}`}
              className="group flex flex-col gap-1 rounded-2xl border border-line bg-surface px-5 py-4 shadow-sm shadow-black/[0.02] transition-colors hover:border-accent/60"
            >
              <span className="font-display text-lg leading-snug text-ink transition-colors group-hover:text-accent">
                {recipe.title}
              </span>
              {facts.length > 0 && (
                <span className="text-xs uppercase tracking-wide text-ink-muted">
                  {facts.join(' · ')}
                </span>
              )}
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
