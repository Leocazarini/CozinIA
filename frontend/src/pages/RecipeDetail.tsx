import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchRecipe, updateRecipe } from '../api/recipes'
import type { UpdateRecipeInput } from '../api/types'
import { RecipeEditForm } from './RecipeEditForm'
import { RecipeView } from './RecipeView'

/**
 * A flat sheet laid over the tiled wall, bleeding past the page gutters.
 *
 * A recipe is the one screen in the app that gets *read* — long ingredient
 * lists and steps — so the azulejo pattern gets covered here rather than
 * sitting behind body text. It wraps every state of the page, including
 * edit mode, so the background doesn't flicker when toggling between them.
 */
function RecipeSheet({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-5 -mt-7 min-h-[70dvh] bg-paper px-5 pt-7 pb-10">{children}</div>
  )
}

export function RecipeDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)

  const {
    data: recipe,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ['recipe', id],
    queryFn: () => fetchRecipe(id as string),
    enabled: Boolean(id),
  })

  const mutation = useMutation({
    mutationFn: (changes: UpdateRecipeInput) => updateRecipe(id as string, changes),
    onSuccess: (updated) => {
      queryClient.setQueryData(['recipe', id], updated)
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
      setIsEditing(false)
    },
  })

  if (isPending) {
    return (
      <RecipeSheet>
        <p className="pt-10 text-center font-display text-sm font-bold tracking-[0.18em] text-ink-muted uppercase">
          Carregando receita…
        </p>
      </RecipeSheet>
    )
  }

  if (isError) {
    return (
      <RecipeSheet>
        <div className="tile tile-keyline px-5 py-6 text-center">
          <p className="font-display font-bold text-ink">{error.message}</p>
        </div>
      </RecipeSheet>
    )
  }

  if (isEditing) {
    return (
      <RecipeSheet>
        <RecipeEditForm
          recipe={recipe}
          onSave={(changes) => mutation.mutate(changes)}
          onCancel={() => setIsEditing(false)}
          isSaving={mutation.isPending}
          errorMessage={mutation.isError ? mutation.error.message : null}
        />
      </RecipeSheet>
    )
  }

  return (
    <RecipeSheet>
      <RecipeView recipe={recipe} onEdit={() => setIsEditing(true)} />
    </RecipeSheet>
  )
}
