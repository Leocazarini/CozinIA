import type { Recipe } from '../api/types'

interface RecipeViewProps {
  recipe: Recipe
  onEdit: () => void
}

function formatFact(label: string, minutes: number | null): string | null {
  return minutes === null ? null : `${label}: ${minutes} min`
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
    <article className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xl font-semibold">{recipe.title}</h2>
        <button type="button" onClick={onEdit} className="shrink-0 underline">
          Editar
        </button>
      </div>

      {recipe.description && <p className="text-neutral-700">{recipe.description}</p>}

      {facts.length > 0 && (
        <p className="text-sm text-neutral-500">{facts.join(' · ')}</p>
      )}

      <section>
        <h3 className="font-medium">Ingredientes</h3>
        {recipe.ingredients.length === 0 ? (
          <p className="text-sm text-neutral-500">Nenhum ingrediente cadastrado.</p>
        ) : (
          <ul className="list-disc pl-5">
            {recipe.ingredients.map((ingredient, index) => (
              <li key={index}>
                {[ingredient.quantity, ingredient.unit, ingredient.name, ingredient.notes]
                  .filter(Boolean)
                  .join(' ')}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="font-medium">Modo de preparo</h3>
        {recipe.steps.length === 0 ? (
          <p className="text-sm text-neutral-500">Nenhum passo cadastrado.</p>
        ) : (
          <ol className="list-decimal pl-5">
            {recipe.steps
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((step) => (
                <li key={step.order}>{step.text}</li>
              ))}
          </ol>
        )}
      </section>
    </article>
  )
}
