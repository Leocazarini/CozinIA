import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { Link } from 'react-router-dom'
import { CookingLoader } from '../components/CookingLoader'
import { MascotLounging } from '../components/Mascot'
import { Quatrefoil } from '../components/icons'
import { createRecipe, createRecipeFromImages, createRecipeFromVideo } from '../api/recipes'

/**
 * A recipe can arrive as a link, as photos, or as a video link, and the three
 * are one flow with three doors: same mutation, same loader, same success
 * screen, and the saved recipe is indistinguishable in the list afterwards.
 *
 * A video gets a field of its own rather than being detected from the link
 * field: reading a Reel as a page and reading it as a video are different
 * things, and which one the user wants is not something to guess from a host.
 */
type Submission =
  | { kind: 'link'; url: string }
  | { kind: 'photos'; files: File[] }
  | { kind: 'video'; url: string }

/** Mirrors MAX_IMAGES in backend/app/services/image_intake.py. */
const MAX_PHOTOS = 8

const ACCEPTED_PHOTO_TYPES = 'image/jpeg,image/png,image/webp'

export function AddRecipe() {
  const [url, setUrl] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [photos, setPhotos] = useState<File[]>([])
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (submission: Submission) => {
      switch (submission.kind) {
        case 'link':
          return createRecipe(submission.url)
        case 'photos':
          return createRecipeFromImages(submission.files)
        case 'video':
          return createRecipeFromVideo(submission.url)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] })
    },
  })

  const previews = useMemo(() => photos.map((photo) => URL.createObjectURL(photo)), [photos])
  // Cleanup runs before the next effect and on unmount, so each batch of
  // object URLs is released as soon as it stops being the current one.
  useEffect(() => () => previews.forEach(URL.revokeObjectURL), [previews])

  function handleSubmitUrl(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ kind: 'link', url })
  }

  function handleSubmitPhotos(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ kind: 'photos', files: photos })
  }

  function handleSubmitVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ kind: 'video', url: videoUrl })
  }

  function handleChoosePhotos(event: ChangeEvent<HTMLInputElement>) {
    const chosen = Array.from(event.target.files ?? [])
    // Appended rather than replaced: photographing a recipe that spans two
    // pages usually means two trips to the picker, and the second one
    // shouldn't discard the first page.
    setPhotos((current) => [...current, ...chosen].slice(0, MAX_PHOTOS))
    // Lets the same file be picked again after being removed — without this
    // the input's value is unchanged and no change event fires.
    event.target.value = ''
  }

  function handleRemovePhoto(index: number) {
    setPhotos((current) => current.filter((_, position) => position !== index))
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
          sobre a viagem da autora à Toscana — e trago só o que interessa. Se a
          receita está num livro ou num caderno, me manda a foto. Se está num
          vídeo, manda o link que eu escuto.
        </p>
      </div>

      {mutation.isPending && <CookingLoader source={mutation.variables?.kind ?? 'link'} />}

      <form
        onSubmit={handleSubmitUrl}
        className="tile-drop flex flex-col gap-5"
        style={{ '--i': 1 } as CSSProperties}
      >
        {/* The top margin is the mascot's room: lounging on the field's top
            edge it reaches ~80px above it, and the label row only accounts
            for part of that. Without this it would climb over the
            paragraph. */}
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
            {/* After the input in the DOM so it paints over the field's top
                border — it is lying *on* the edge, not tucked behind it.
                Hidden while the pot is busy cooking downstairs in the
                loader: two of the same mascot on screen breaks the gag.
                The negative margin (not translate-y: the `translate`
                property belongs to the focus lift) drops the artwork's
                below-line overhang past the border so the body settles
                onto it. */}
            {!mutation.isPending && (
              <MascotLounging className="mascot-lift pointer-events-none absolute right-0 bottom-full z-10 mb-[-10px] w-[190px]" />
            )}
          </div>
        </div>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="tile tile-flat tile-pressable bg-accent py-3.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55"
        >
          {mutation.isPending ? 'Extraindo receita…' : 'Adicionar receita'}
        </button>
      </form>

      <div
        className="tile-drop flex items-center gap-3"
        style={{ '--i': 2 } as CSSProperties}
        aria-hidden="true"
      >
        <span className="h-0.5 flex-1 bg-ink/15" />
        <span className="font-display text-[0.7rem] font-extrabold tracking-[0.2em] text-ink-muted uppercase">
          ou
        </span>
        <span className="h-0.5 flex-1 bg-ink/15" />
      </div>

      <form
        onSubmit={handleSubmitPhotos}
        className="tile-drop flex flex-col gap-4"
        style={{ '--i': 3 } as CSSProperties}
      >
        <div className="flex flex-col gap-2">
          <label
            htmlFor="recipe-photos"
            className="font-display text-xs font-extrabold tracking-[0.18em] text-ink uppercase"
          >
            Fotos da receita
          </label>
          <p className="text-xs leading-relaxed text-ink-muted">
            Página de livro, caderno, print. Se a receita ocupa mais de uma
            página, mande todas na ordem — eu junto tudo numa receita só.
          </p>
          <input
            id="recipe-photos"
            type="file"
            multiple
            accept={ACCEPTED_PHOTO_TYPES}
            onChange={handleChoosePhotos}
            disabled={mutation.isPending}
            className="field w-full cursor-pointer px-4 py-3 text-sm file:mr-3 file:cursor-pointer file:border-0 file:bg-transparent file:font-display file:text-xs file:font-extrabold file:tracking-[0.14em] file:text-accent file:uppercase"
          />
        </div>

        {photos.length > 0 && (
          <ul className="grid grid-cols-3 gap-3">
            {photos.map((photo, index) => (
              <li key={`${photo.name}-${index}`} className="tile relative overflow-hidden">
                <img
                  src={previews[index]}
                  alt={`Foto ${index + 1} da receita`}
                  className="aspect-square w-full object-cover"
                />
                {/* The number, not the filename: photos straight from a
                    camera are all called the same thing, and what matters
                    here is which page comes first. */}
                <span className="absolute top-1 left-1 flex h-5 w-5 items-center justify-center border-2 border-ink bg-paper font-display text-[0.65rem] font-extrabold text-ink">
                  {index + 1}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemovePhoto(index)}
                  disabled={mutation.isPending}
                  aria-label={`Remover foto ${index + 1}`}
                  className="absolute top-1 right-1 flex h-5 w-5 items-center justify-center border-2 border-ink bg-accent font-display text-[0.7rem] font-extrabold text-accent-ink"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || photos.length === 0}
          className="tile tile-flat tile-pressable bg-accent py-3.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55"
        >
          {mutation.isPending ? 'Lendo as fotos…' : 'Extrair das fotos'}
        </button>
      </form>

      <div
        className="tile-drop flex items-center gap-3"
        style={{ '--i': 4 } as CSSProperties}
        aria-hidden="true"
      >
        <span className="h-0.5 flex-1 bg-ink/15" />
        <span className="font-display text-[0.7rem] font-extrabold tracking-[0.2em] text-ink-muted uppercase">
          ou
        </span>
        <span className="h-0.5 flex-1 bg-ink/15" />
      </div>

      <form
        onSubmit={handleSubmitVideo}
        className="tile-drop flex flex-col gap-4"
        style={{ '--i': 5 } as CSSProperties}
      >
        <div className="flex flex-col gap-2">
          <label
            htmlFor="recipe-video-url"
            className="font-display text-xs font-extrabold tracking-[0.18em] text-ink uppercase"
          >
            Link do vídeo
          </label>
          <p className="text-xs leading-relaxed text-ink-muted">
            Reel, Short, TikTok. Eu escuto o que a pessoa fala, leio a legenda do
            post, e junto as duas coisas numa receita. Costuma demorar mais que
            as outras — vale a espera.
          </p>
          <div className="field-nest relative">
            <input
              id="recipe-video-url"
              type="url"
              required
              placeholder="https://… aquele reel que você salvou"
              value={videoUrl}
              onChange={(event) => setVideoUrl(event.target.value)}
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
          {mutation.isPending ? 'Assistindo o vídeo…' : 'Extrair do vídeo'}
        </button>
      </form>

      {mutation.isError && (
        <p role="alert" className="border-l-4 border-accent pl-3 text-sm font-medium text-ink">
          {mutation.error.message}
        </p>
      )}
    </div>
  )
}
