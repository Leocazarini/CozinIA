import type { CSSProperties, ReactNode } from 'react'
import { Quatrefoil } from '../components/icons'
import type { Recipe } from '../api/types'

interface RecipeViewProps {
  recipe: Recipe
  onEdit: () => void
}

interface Fact {
  label: string
  value: string
}

function timeFact(label: string, minutes: number | null): Fact | null {
  return minutes === null ? null : { label, value: `${minutes} min` }
}

/** Chips cycle through the palette so a row of them reads as painted tiles. */
const CHIP_TONES = ['text-tile', 'text-leaf', 'text-accent'] as const

/** Section title closed by the dogtooth frieze, as on a real tile panel. */
function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h3 className="font-display text-sm font-extrabold tracking-[0.2em] text-ink uppercase">
        {children}
      </h3>
      <div className="frieze" aria-hidden="true" />
    </div>
  )
}

/** Read-only display of a saved recipe. */
export function RecipeView({ recipe, onEdit }: RecipeViewProps) {
  const facts = [
    recipe.servings !== null ? { label: 'Porções', value: `${recipe.servings}` } : null,
    timeFact('Preparo', recipe.prep_time_minutes),
    timeFact('Cozimento', recipe.cook_time_minutes),
    timeFact('Total', recipe.total_time_minutes),
  ].filter((fact): fact is Fact => fact !== null)

  return (
    <article className="flex flex-col gap-7">
      <header
        className="tile tile-keyline tile-drop flex flex-col gap-3 px-5 py-5"
        style={{ '--i': 0 } as CSSProperties}
      >
        <div className="flex items-start justify-between gap-3">
          <span
            aria-hidden="true"
            className="font-display text-[0.65rem] font-extrabold tracking-[0.24em] text-ink-muted uppercase"
          >
            Receita
          </span>
          <button
            type="button"
            onClick={onEdit}
            className="tile tile-pressable shrink-0 px-3 py-1.5 font-display text-[0.7rem] font-extrabold tracking-[0.14em] text-ink uppercase"
          >
            Editar
          </button>
        </div>

        <h2 className="font-display text-3xl leading-[1.05] font-extrabold tracking-[-0.03em] text-balance text-ink">
          {recipe.title}
        </h2>

        {recipe.description && (
          <p className="text-[0.95rem] leading-relaxed text-ink-muted">{recipe.description}</p>
        )}

        <Quatrefoil className="h-5 w-5 self-end text-tile" />
      </header>

      {facts.length > 0 && (
        <ul
          className="tile-drop flex flex-wrap gap-2.5"
          style={{ '--i': 1 } as CSSProperties}
        >
          {facts.map((fact, index) => (
            <li
              key={fact.label}
              className="tile flex flex-col items-start px-3 py-1.5 leading-tight"
            >
              <span className="font-display text-[0.6rem] font-bold tracking-[0.16em] text-ink-muted uppercase">
                {fact.label}
              </span>
              <span
                className={`font-display text-base font-extrabold ${CHIP_TONES[index % CHIP_TONES.length]}`}
              >
                {fact.value}
              </span>
            </li>
          ))}
        </ul>
      )}

      <section
        className="tile-drop flex flex-col gap-4"
        style={{ '--i': 2 } as CSSProperties}
      >
        <SectionHeading>Ingredientes</SectionHeading>
        {recipe.ingredients.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum ingrediente cadastrado.</p>
        ) : (
          <ul className="flex flex-col gap-2.5">
            {recipe.ingredients.map((ingredient, index) => {
              const measure = [ingredient.quantity, ingredient.unit].filter(Boolean).join(' ')
              const name = [ingredient.name, ingredient.notes].filter(Boolean).join(' ')

              return (
                <li key={index} className="flex items-baseline gap-3">
                  <span
                    aria-hidden="true"
                    className="mt-1 h-2.5 w-2.5 shrink-0 rotate-45 border-2 border-tile"
                  />
                  {measure && (
                    <span className="shrink-0 font-display text-sm font-extrabold tabular-nums text-accent">
                      {measure}
                    </span>
                  )}
                  <span className="text-ink">{name}</span>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section
        className="tile-drop flex flex-col gap-4"
        style={{ '--i': 3 } as CSSProperties}
      >
        <SectionHeading>Modo de preparo</SectionHeading>
        {recipe.steps.length === 0 ? (
          <p className="text-sm text-ink-muted">Nenhum passo cadastrado.</p>
        ) : (
          <ol className="flex flex-col gap-4">
            {recipe.steps
              .slice()
              .sort((a, b) => a.order - b.order)
              .map((step) => (
                <li key={step.order} className="flex gap-3.5">
                  {/* The <ol> already conveys the ordering to assistive
                      tech — this numeral is the visual echo of it. */}
                  <span
                    aria-hidden="true"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[3px] border-2 border-ink bg-accent font-display text-sm font-extrabold text-accent-ink shadow-[3px_3px_0_0_var(--color-emboss)]"
                  >
                    {step.order}
                  </span>
                  <span className="pt-1 leading-relaxed text-ink">{step.text}</span>
                </li>
              ))}
          </ol>
        )}
      </section>
    </article>
  )
}
