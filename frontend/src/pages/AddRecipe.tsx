import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type CSSProperties, type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { CookingLoader } from '../components/CookingLoader'
import { MascotLeaning } from '../components/Mascot'
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
      <div className="tile-drop flex flex-col gap-2" style={{ '--i': 0 } as CSSProperties}>
        <h2 className="font-display text-[1.9rem] leading-[1.05] font-extrabold tracking-[-0.03em] text-ink">
          O que vamos <span className="text-accent">cozinhar</span> hoje?
        </h2>
        <p className="text-sm leading-relaxed text-ink-muted">
          Cole o link e deixa comigo. Eu leio a página inteira — inclusive a parte
          sobre a viagem da autora à Toscana — e trago só o que interessa.
        </p>
      </div>

      {mutation.isPending && <CookingLoader />}

      <form
        onSubmit={handleSubmit}
        className="tile-drop flex flex-col gap-5"
        style={{ '--i': 1 } as CSSProperties}
      >
        {/* The top margin is the mascot's room: it is anchored to the field's
            top edge and reaches ~85px above it. Without this it would climb
            over the paragraph. */}
        <div className="mt-16 flex flex-col gap-2">
          <label
            htmlFor="recipe-url"
            className="font-display text-xs font-extrabold tracking-[0.18em] text-ink uppercase"
          >
            Link da receita
          </label>
          {/* `field-nest` is the hook the stylesheet uses to perk the mascot
              up while the input has focus — see index.css. */}
          <div className="field-nest relative">
            {/* Hidden while the pot is busy cooking downstairs in the
                loader: two of the same mascot on screen breaks the gag. */}
            {!mutation.isPending && (
              <MascotLeaning className="pointer-events-none absolute right-1 bottom-full z-10 w-[104px] translate-y-[16px]" />
            )}
            <input
              id="recipe-url"
              type="url"
              required
              placeholder="https://… pode ser aquele blog gigante"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              disabled={mutation.isPending}
              className="field w-full px-4 py-3"
            />
          </div>
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
