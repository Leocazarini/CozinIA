import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
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
      <div className="flex flex-col items-start gap-3 pt-6">
        <p className="font-display text-xl italic leading-snug text-ink">
          Receita <span className="text-accent">{recipe.title}</span> salva com sucesso!
        </p>
        <Link
          to="/"
          className="text-sm font-medium text-ink-muted underline decoration-line underline-offset-4 transition-colors hover:text-accent"
        >
          Ver receitas
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 pt-2">
      <div className="flex flex-col gap-2">
        <label htmlFor="recipe-url" className="font-display text-lg italic text-ink">
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
          className="rounded-xl border border-line bg-paper px-4 py-3 text-ink placeholder:text-ink-muted/70 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-50"
        />
      </div>
      <button
        type="submit"
        disabled={mutation.isPending}
        className="rounded-xl bg-accent py-3 font-medium text-accent-ink transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {mutation.isPending ? 'Extraindo receita…' : 'Adicionar receita'}
      </button>
      {mutation.isError && (
        <p role="alert" className="text-sm text-accent">
          {mutation.error.message}
        </p>
      )}
    </form>
  )
}
