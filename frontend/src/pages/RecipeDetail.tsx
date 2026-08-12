import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchRecipe, updateRecipe } from '../api/recipes'
import type { UpdateRecipeInput } from '../api/types'
import { RecipeEditForm } from './RecipeEditForm'
import { RecipeView } from './RecipeView'

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
    return <p>Carregando receita…</p>
  }

  if (isError) {
    return <p>{error.message}</p>
  }

  if (isEditing) {
    return (
      <RecipeEditForm
        recipe={recipe}
        onSave={(changes) => mutation.mutate(changes)}
        onCancel={() => setIsEditing(false)}
        isSaving={mutation.isPending}
        errorMessage={mutation.isError ? mutation.error.message : null}
      />
    )
  }

  return <RecipeView recipe={recipe} onEdit={() => setIsEditing(true)} />
}
