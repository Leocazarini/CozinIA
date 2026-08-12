import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type CSSProperties, type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Quatrefoil } from '../components/icons'
import { createRecipe } from '../api/recipes'

export function AddRecipe() {
  const [url, setUrl] = useState('')
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: createRecipe,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
    },
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate(url)
  }

  if (mutation.isSuccess) {
    const recipe = mutation.data
    return (
      <div className="flex flex-col items-start gap-5 pt-2">
        <div className="tile tile-keyline tile-drop flex w-full flex-col gap-3 px-5 py-6">
          <Quatrefoil className="h-7 w-7 text-leaf" />
          <p className="font-display text-2xl leading-tight font-extrabold tracking-[-0.02em] text-ink">
            <span className="text-accent">{recipe.title}</span>
          </p>
          <p className="font-display text-sm font-bold tracking-[0.16em] text-ink-muted uppercase">
            salva no receitário
          </p>
        </div>
        <Link
          to="/"
          className="tile tile-pressable px-4 py-2 font-display text-[0.72rem] font-extrabold tracking-[0.14em] text-ink uppercase"
        >
          Ver receitas
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div
        className="tile tile-drop flex items-start gap-3 px-4 py-4"
        style={{ '--i': 0 } as CSSProperties}
      >
        <Quatrefoil className="mt-0.5 h-5 w-5 shrink-0 text-tile" />
        <p className="text-sm leading-relaxed text-ink-muted">
          Cole o link e a <span className="font-bold text-accent">IA</span> lê a página por você:
          ingredientes, modo de preparo, tempos e porções.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="tile-drop flex flex-col gap-5"
        style={{ '--i': 1 } as CSSProperties}
      >
        <div className="flex flex-col gap-2">
          <label
            htmlFor="recipe-url"
            className="font-display text-xs font-extrabold tracking-[0.18em] text-ink uppercase"
          >
            Link da receita
          </label>
          <input
            id="recipe-url"
            type="url"
            required
            placeholder="https://..."
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={mutation.isPending}
            className="field px-4 py-3"
          />
        </div>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="tile tile-flat tile-pressable bg-accent py-3.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55"
        >
          {mutation.isPending ? 'Extraindo receita…' : 'Adicionar receita'}
        </button>
        {mutation.isError && (
          <p
            role="alert"
            className="border-l-4 border-accent pl-3 text-sm font-medium text-ink"
          >
            {mutation.error.message}
          </p>
        )}
      </form>
    </div>
  )
}
