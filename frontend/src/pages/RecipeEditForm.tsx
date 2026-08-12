import { type FormEvent, useState } from 'react'
import type { Ingredient, Recipe, Step, UpdateRecipeInput } from '../api/types'

interface RecipeEditFormProps {
  recipe: Recipe
  onSave: (changes: UpdateRecipeInput) => void
  onCancel: () => void
  isSaving: boolean
  errorMessage: string | null
}

function numberOrNull(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

const fieldClassName = 'field px-3 py-2'
const labelClassName =
  'font-display text-[0.68rem] font-extrabold tracking-[0.16em] text-ink-muted uppercase'
const ghostButtonClassName =
  'font-display text-[0.68rem] font-extrabold tracking-[0.14em] text-accent uppercase underline decoration-2 underline-offset-4 transition-colors hover:text-ink'
const fieldsetClassName = 'tile flex flex-col gap-4 px-4 py-4'
const legendClassName =
  'mx-1 rounded-[2px] bg-surface px-2 font-display text-xs font-extrabold tracking-[0.2em] text-ink uppercase'

/** Manual edit form for correcting whatever the AI extraction got wrong. */
export function RecipeEditForm({
  recipe,
  onSave,
  onCancel,
  isSaving,
  errorMessage,
}: RecipeEditFormProps) {
  const [title, setTitle] = useState(recipe.title)
  const [description, setDescription] = useState(recipe.description ?? '')
  const [servings, setServings] = useState(recipe.servings?.toString() ?? '')
  const [prepTime, setPrepTime] = useState(recipe.prep_time_minutes?.toString() ?? '')
  const [cookTime, setCookTime] = useState(recipe.cook_time_minutes?.toString() ?? '')
  const [totalTime, setTotalTime] = useState(recipe.total_time_minutes?.toString() ?? '')
  const [ingredients, setIngredients] = useState<Ingredient[]>(recipe.ingredients)
  const [steps, setSteps] = useState<Step[]>(recipe.steps)

  function updateIngredient(index: number, changes: Partial<Ingredient>) {
    setIngredients((current) =>
      current.map((ingredient, i) => (i === index ? { ...ingredient, ...changes } : ingredient)),
    )
  }

  function addIngredient() {
    setIngredients((current) => [...current, { name: '', quantity: null, unit: null, notes: null }])
  }

  function removeIngredient(index: number) {
    setIngredients((current) => current.filter((_, i) => i !== index))
  }

  function updateStepText(index: number, text: string) {
    setSteps((current) => current.map((step, i) => (i === index ? { ...step, text } : step)))
  }

  function addStep() {
    setSteps((current) => [...current, { order: current.length + 1, text: '' }])
  }

  function removeStep(index: number) {
    setSteps((current) => current.filter((_, i) => i !== index))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave({
      title,
      description: description.trim() === '' ? null : description,
      servings: numberOrNull(servings),
      prep_time_minutes: numberOrNull(prepTime),
      cook_time_minutes: numberOrNull(cookTime),
      total_time_minutes: numberOrNull(totalTime),
      ingredients,
      steps: steps.map((step, index) => ({ ...step, order: index + 1 })),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="recipe-title" className={labelClassName}>
          Título
        </label>
        <input
          id="recipe-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
          className={`${fieldClassName} font-display text-lg font-extrabold tracking-[-0.02em]`}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="recipe-description" className={labelClassName}>
          Descrição
        </label>
        <textarea
          id="recipe-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className={fieldClassName}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="recipe-servings" className={labelClassName}>
            Porções
          </label>
          <input
            id="recipe-servings"
            type="number"
            min={0}
            value={servings}
            onChange={(event) => setServings(event.target.value)}
            className={`w-20 ${fieldClassName}`}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="recipe-prep-time" className={labelClassName}>
            Preparo (min)
          </label>
          <input
            id="recipe-prep-time"
            type="number"
            min={0}
            value={prepTime}
            onChange={(event) => setPrepTime(event.target.value)}
            className={`w-20 ${fieldClassName}`}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="recipe-cook-time" className={labelClassName}>
            Cozimento (min)
          </label>
          <input
            id="recipe-cook-time"
            type="number"
            min={0}
            value={cookTime}
            onChange={(event) => setCookTime(event.target.value)}
            className={`w-20 ${fieldClassName}`}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="recipe-total-time" className={labelClassName}>
            Total (min)
          </label>
          <input
            id="recipe-total-time"
            type="number"
            min={0}
            value={totalTime}
            onChange={(event) => setTotalTime(event.target.value)}
            className={`w-20 ${fieldClassName}`}
          />
        </div>
      </div>

      <fieldset className={fieldsetClassName}>
        <legend className={legendClassName}>Ingredientes</legend>
        {ingredients.map((ingredient, index) => (
          <div
            key={index}
            className="flex flex-wrap items-end gap-2 border-b-2 border-line pb-3 last:border-none last:pb-0"
          >
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`ingredient-name-${index}`} className={labelClassName}>
                Nome do ingrediente {index + 1}
              </label>
              <input
                id={`ingredient-name-${index}`}
                value={ingredient.name}
                onChange={(event) => updateIngredient(index, { name: event.target.value })}
                required
                className={fieldClassName}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`ingredient-quantity-${index}`} className={labelClassName}>
                Quantidade do ingrediente {index + 1}
              </label>
              <input
                id={`ingredient-quantity-${index}`}
                value={ingredient.quantity ?? ''}
                onChange={(event) =>
                  updateIngredient(index, { quantity: event.target.value || null })
                }
                className={`w-24 ${fieldClassName}`}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={`ingredient-unit-${index}`} className={labelClassName}>
                Unidade do ingrediente {index + 1}
              </label>
              <input
                id={`ingredient-unit-${index}`}
                value={ingredient.unit ?? ''}
                onChange={(event) => updateIngredient(index, { unit: event.target.value || null })}
                className={`w-24 ${fieldClassName}`}
              />
            </div>
            <button
              type="button"
              onClick={() => removeIngredient(index)}
              className={`pb-2 ${ghostButtonClassName}`}
            >
              Remover
            </button>
          </div>
        ))}
        <button type="button" onClick={addIngredient} className={`self-start ${ghostButtonClassName}`}>
          Adicionar ingrediente
        </button>
      </fieldset>

      <fieldset className={fieldsetClassName}>
        <legend className={legendClassName}>Modo de preparo</legend>
        {steps.map((step, index) => (
          <div key={index} className="flex flex-col gap-1.5">
            <label htmlFor={`step-text-${index}`} className={labelClassName}>
              Passo {index + 1}
            </label>
            <div className="flex items-start gap-2">
              <textarea
                id={`step-text-${index}`}
                value={step.text}
                onChange={(event) => updateStepText(index, event.target.value)}
                required
                className={`flex-1 ${fieldClassName}`}
              />
              <button
                type="button"
                onClick={() => removeStep(index)}
                className={`pt-2 ${ghostButtonClassName}`}
              >
                Remover
              </button>
            </div>
          </div>
        ))}
        <button type="button" onClick={addStep} className={`self-start ${ghostButtonClassName}`}>
          Adicionar passo
        </button>
      </fieldset>

      <div className="flex items-center gap-5">
        <button
          type="submit"
          disabled={isSaving}
          className="tile tile-flat tile-pressable bg-accent px-6 py-2.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55"
        >
          {isSaving ? 'Salvando…' : 'Salvar'}
        </button>
        <button type="button" onClick={onCancel} disabled={isSaving} className={ghostButtonClassName}>
          Cancelar
        </button>
      </div>

      {errorMessage && (
        <p role="alert" className="border-l-4 border-accent pl-3 text-sm font-medium text-ink">
          {errorMessage}
        </p>
      )}
    </form>
  )
}
