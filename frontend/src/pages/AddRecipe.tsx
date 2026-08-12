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
      <div className="flex flex-col gap-3">
        <p>
          Receita <strong>{recipe.title}</strong> salva com sucesso!
        </p>
        <Link to="/" className="underline">
          Ver receitas
        </Link>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label htmlFor="recipe-url">Link da receita</label>
      <input
        id="recipe-url"
        type="url"
        required
        placeholder="https://..."
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        disabled={mutation.isPending}
        className="rounded-md border border-neutral-300 px-3 py-2"
      />
      <button
        type="submit"
        disabled={mutation.isPending}
        className="rounded-md bg-neutral-900 py-2 text-white disabled:opacity-50"
      >
        {mutation.isPending ? 'Extraindo receita…' : 'Adicionar receita'}
      </button>
      {mutation.isError && <p role="alert">{mutation.error.message}</p>}
    </form>
  )
}
