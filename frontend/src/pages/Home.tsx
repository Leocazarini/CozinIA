import { useQuery } from '@tanstack/react-query'
import { fetchRecipes } from '../api/recipes'

export function Home() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['recipes'],
    queryFn: fetchRecipes,
  })

  if (isPending) {
    return <p>Carregando receitas…</p>
  }

  if (isError) {
    return <p>Não foi possível carregar as receitas. Tente novamente.</p>
  }

  if (data.length === 0) {
    return <p>Nenhuma receita salva ainda.</p>
  }

  return (
    <ul className="flex flex-col gap-3">
      {data.map((recipe) => (
        <li key={recipe.id} className="rounded-lg border border-neutral-200 p-3">
          <h2 className="font-medium">{recipe.title}</h2>
        </li>
      ))}
    </ul>
  )
}
