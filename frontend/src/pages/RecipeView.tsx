import type { Recipe } from '../api/types'

interface RecipeViewProps {
  recipe: Recipe
  onEdit: () => void
}

function formatFact(label: string, minutes: number | null): string | null {
  return minutes === null ? null : `${label} ${minutes} min`
}

/** Read-only display of a saved recipe. */
export function RecipeView({ recipe, onEdit }: RecipeViewProps) {
  const facts = [
    recipe.servings !== null ? `${recipe.servings} porções` : null,
    formatFact('Preparo', recipe.prep_time_minutes),
    formatFact('Cozimento', recipe.cook_time_minutes),
    formatFact('Total', recipe.total_time_minutes),
  ].filter((fact): fact is string => fact !== null)

  return (
    <article className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <h2 className="font-display text-2xl leading-tight text-ink">{recipe.title}</h2>
        <button
          type="button"
          onClick={onEdit}
          className="shrink-0 rounded-full border border-line px-3 py-1 text-xs font-medium text-ink-muted transition-colors hover:border-accent hover:text-accent"
        >
          Editar
        </button>
      </div>

      {recipe.description && (
        <p className="font-display italic leading-relaxed text-ink-muted">{recipe.description}</p>
      )}

      {facts.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {facts.map((fact) => (
            <li
              key={fact}
              className="rounded-full bg-accent-soft px-3 py-1 text-xs uppercase tracking-wide text-accent"
            >
              {fact}
            </li>
          ))}
        </ul>
      )}

      <section className="flex flex-col gap-3">
        <h3 className="border-b border-line pb-1 font-display text-lg italic text-ink">
          Ingredientes
        </h3>
        {recipe.ingredients.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum ingrediente cadastrado.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-baseline gap-2 text-ink">
                <span aria-hidden="true" className="text-accent">
                  •
                </span>
                <span>
                  {[ingredient.quantity, ingredient.unit, ingredient.name, ingredient.notes]
                    .filter(Boolean)
                    .join(' ')}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="border-b border-line pb-1 font-display text-lg italic text-ink">
          Modo de preparo
        </h3>
        {recipe.steps.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum passo cadastrado.</p>
        ) : (
          <ol className="flex flex-col gap-4">
            {recipe.steps
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((step) => (
                <li key={step.order} className="flex gap-3">
                  <span className="font-display text-lg italic text-accent">{step.order}</span>
                  <span className="pt-0.5 text-ink">{step.text}</span>
                </li>
              ))}
          </ol>
        )}
      </section>
    </article>
  )
}
