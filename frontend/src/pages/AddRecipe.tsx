import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { Link } from 'react-router-dom'
import { CookingLoader } from '../components/CookingLoader'
import { MascotFilming, MascotLounging, MascotSnapping } from '../components/Mascot'
import { CameraIcon, LinkIcon, Quatrefoil, VideoIcon } from '../components/icons'
import { createRecipe, createRecipeFromImages, createRecipeFromVideo } from '../api/recipes'
import { useOnlineStatus } from '../hooks/useOnlineStatus'

/**
 * A recipe can arrive as photos, as a video link, or as a link, and the
 * three are one flow with three doors: same mutation, same loader, same
 * success screen, and the saved recipe is indistinguishable in the list
 * afterwards.
 *
 * A video gets a door of its own rather than being detected from the link
 * field: reading a Reel as a page and reading it as a video are different
 * things, and which one the user wants is not something to guess from a
 * host.
 */
type Submission =
  | { kind: 'link'; url: string }
  | { kind: 'photos'; files: File[] }
  | { kind: 'video'; url: string }

type Door = Submission['kind']

/**
 * Photos first: the door that has no other home. A link can be pasted
 * anywhere, but a recipe on paper only exists here.
 */
const DOORS = [
  { id: 'photos', label: 'Imagem', Icon: CameraIcon },
  { id: 'video', label: 'Vídeo', Icon: VideoIcon },
  { id: 'link', label: 'Link', Icon: LinkIcon },
] as const satisfies readonly { id: Door; label: string; Icon: typeof CameraIcon }[]

/**
 * Hand-stuck, not machine-laid: each tab leans a hair. The lean belongs to
 * the position, not to the selection, so opening another door never makes
 * the strip twitch.
 */
const LEANS = ['-0.7deg', '0.5deg', '-0.4deg']

/** Mirrors MAX_IMAGES in backend/app/services/image_intake.py. */
const MAX_PHOTOS = 8

const ACCEPTED_PHOTO_TYPES = 'image/jpeg,image/png,image/webp'

const BUTTON_CLASS =
  'tile tile-flat tile-pressable bg-accent py-3.5 font-display text-sm font-extrabold tracking-[0.14em] text-accent-ink uppercase disabled:opacity-55'

const LABEL_CLASS = 'font-display text-xs font-extrabold tracking-[0.18em] text-ink uppercase'

/**
 * The tab strip, right under the header. Three glazed tiles: the open one
 * is filled with urucum and stamped onto the wall, the closed ones are
 * unglazed outlines. The lozenge hanging off the open tile is the same
 * shape the azulejo grid splits across its edges, pointing at the panel it
 * belongs to.
 */
function DoorTabs({ open, onOpen }: { open: Door; onOpen: (door: Door) => void }) {
  const tabs = useRef(new Map<Door, HTMLButtonElement>())

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const steps: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 }
    const step = steps[event.key]
    if (step === undefined) return
    event.preventDefault()
    const current = DOORS.findIndex((door) => door.id === open)
    const next = DOORS[(current + step + DOORS.length) % DOORS.length].id
    onOpen(next)
    tabs.current.get(next)?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="De onde vem a receita"
      className="tile-drop flex gap-2"
      style={{ '--i': 0 } as CSSProperties}
    >
      {DOORS.map(({ id, label, Icon }, index) => {
        const isOpen = id === open
        return (
          <button
            key={id}
            ref={(node) => {
              if (node) tabs.current.set(id, node)
            }}
            type="button"
            role="tab"
            id={`door-${id}`}
            aria-selected={isOpen}
            aria-controls={`panel-${id}`}
            tabIndex={isOpen ? 0 : -1}
            onClick={() => onOpen(id)}
            onKeyDown={handleKeyDown}
            style={{ rotate: LEANS[index] }}
            className={[
              // min-h-11: a thumb's worth of tab (44px), which py-2.5 alone
              // was 4px short of.
              'relative flex min-h-11 flex-1 items-center justify-center gap-1.5 rounded-[4px] border-2 py-2.5 font-display text-[0.7rem] font-extrabold tracking-[0.12em] uppercase transition-colors duration-150',
              isOpen
                ? 'tile tile-flat tile-pressable border-ink bg-accent text-accent-ink'
                : 'border-ink/25 bg-surface/55 text-ink-muted hover:border-ink hover:text-ink',
            ].join(' ')}
          >
            <Icon className="h-4 w-4" />
            {label}
            {isOpen && (
              <span
                aria-hidden="true"
                className="absolute -bottom-[7px] left-1/2 h-2.5 w-2.5 -translate-x-1/2 rotate-45 border-2 border-ink bg-accent"
              />
            )}
          </button>
        )
      })}
    </div>
  )
}

/**
 * A field with a mascot standing on its top edge. The pose comes last in
 * the DOM so it paints over the field's real border — it is standing *on*
 * the line, not tucked behind it — and `room` is the space above the field
 * the pose needs, so it never climbs over the copy. `field-nest` is the
 * hook the stylesheet uses to perk the pose up while the input has focus
 * (see index.css).
 *
 * With no pose (an extraction is running, and the mascot is downstairs in
 * the loader), the room goes away with it: reserving a mascot's worth of
 * empty wall for nobody just leaves a hole in the page.
 */
function MascotStage({
  children,
  room,
  pose,
}: {
  children: ReactNode
  room: string
  pose: ReactNode
}) {
  return (
    <div className={`field-nest relative ${pose ? room : ''}`}>
      {children}
      {pose}
    </div>
  )
}

export function AddRecipe() {
  const isOnline = useOnlineStatus()
  const [open, setOpen] = useState<Door>('photos')
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

  function handleOpen(door: Door) {
    setOpen(door)
    // An error belongs to the door it happened in — carrying it to the next
    // one would blame the wrong field. A request already in flight keeps its
    // loader, though: it is still running whichever door is on screen.
    if (!mutation.isPending) mutation.reset()
  }

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
      <DoorTabs open={open} onOpen={handleOpen} />

      {/* The saved recipes still open with no signal — the service worker
          answers with what was already read — so silence here would look
          like the app simply not working. Reading is offline; extracting
          is not, and only this screen has to say it. */}
      {!isOnline && (
        <p role="status" className="tile tile-keyline px-4 py-3 text-sm leading-relaxed text-ink">
          <span className="font-display font-extrabold tracking-[0.06em]">Sem conexão.</span> As
          receitas que você já abriu continuam aqui, mas para trazer uma nova eu preciso de
          internet.
        </p>
      )}

      {/* Keyed by door so the panel drops onto the wall again on every
          switch, the same entrance every other tile makes. */}
      <div
        key={open}
        role="tabpanel"
        id={`panel-${open}`}
        aria-labelledby={`door-${open}`}
        className="flex flex-col gap-6"
      >
        {open === 'photos' && (
          <>
            <div className="tile-drop flex flex-col gap-2" style={{ '--i': 1 } as CSSProperties}>
              <h2 className="font-display text-[1.7rem] leading-[1.05] font-extrabold tracking-[-0.03em] text-ink">
                A receita está no <span className="text-accent">papel</span>?
              </h2>
              <p className="text-sm leading-relaxed text-ink-muted">
                Página de livro, caderno, print — manda a foto que eu decifro.
                Se a receita ocupa mais de uma página, manda todas na ordem: eu
                junto tudo numa receita só.
              </p>
            </div>

            {mutation.isPending && <CookingLoader source="photos" />}

            <form
              onSubmit={handleSubmitPhotos}
              className="tile-drop flex flex-col gap-4"
              style={{ '--i': 2 } as CSSProperties}
            >
              <div className="flex flex-col gap-2">
                <label htmlFor="recipe-photos" className={LABEL_CLASS}>
                  Fotos da receita
                </label>
                <MascotStage
                  room="mt-30"
                  pose={
                    !mutation.isPending && (
                      <MascotSnapping className="mascot-lift pointer-events-none absolute right-1 bottom-full z-10 mb-[-9px] w-[106px]" />
                    )
                  }
                >
                  <input
                    id="recipe-photos"
                    type="file"
                    multiple
                    accept={ACCEPTED_PHOTO_TYPES}
                    onChange={handleChoosePhotos}
                    disabled={mutation.isPending}
                    className="field w-full cursor-pointer px-4 py-3 text-sm file:mr-3 file:cursor-pointer file:border-0 file:bg-transparent file:font-display file:text-xs file:font-extrabold file:tracking-[0.14em] file:text-accent file:uppercase"
                  />
                </MascotStage>

                {/* The other way in, for the book that is open on the counter
                    right now. It needs an input of its own: `capture` on the
                    picker above would replace it with the camera and take
                    away the screenshot-saved-yesterday case. The input stays
                    focusable (never `hidden`) so the keyboard can reach it —
                    the label is only what it looks like. */}
                <input
                  id="recipe-camera"
                  type="file"
                  accept={ACCEPTED_PHOTO_TYPES}
                  capture="environment"
                  onChange={handleChoosePhotos}
                  disabled={mutation.isPending}
                  className="sr-only"
                />
                <label
                  htmlFor="recipe-camera"
                  className="tile tile-pressable inline-flex min-h-11 cursor-pointer items-center gap-2 self-start px-4 py-2 font-display text-[0.72rem] font-extrabold tracking-[0.14em] text-ink uppercase"
                >
                  <CameraIcon className="h-4 w-4" />
                  Tirar foto
                </label>
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
                          camera are all called the same thing, and what
                          matters here is which page comes first. */}
                      <span className="absolute top-1 left-1 flex h-5 w-5 items-center justify-center border-2 border-ink bg-paper font-display text-[0.65rem] font-extrabold text-ink">
                        {index + 1}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemovePhoto(index)}
                        disabled={mutation.isPending}
                        aria-label={`Remover foto ${index + 1}`}
                        // Same trick as the theme toggle: the badge stays
                        // small so it doesn't cover the photo, while the
                        // touchable area around it grows to a thumb's size.
                        className="absolute top-1 right-1 flex h-5 w-5 items-center justify-center border-2 border-ink bg-accent font-display text-[0.7rem] font-extrabold text-accent-ink after:absolute after:-inset-2.5 after:content-['']"
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <button
                type="submit"
                disabled={mutation.isPending || photos.length === 0 || !isOnline}
                className={BUTTON_CLASS}
              >
                {mutation.isPending ? 'Lendo as fotos…' : 'Extrair das fotos'}
              </button>
            </form>
          </>
        )}

        {open === 'video' && (
          <>
            <div className="tile-drop flex flex-col gap-2" style={{ '--i': 1 } as CSSProperties}>
              <h2 className="font-display text-[1.7rem] leading-[1.05] font-extrabold tracking-[-0.03em] text-ink">
                Achou num <span className="text-accent">vídeo</span>?
              </h2>
              <p className="text-sm leading-relaxed text-ink-muted">
                Reel, Short, TikTok. Eu escuto o que a pessoa fala, leio a
                legenda do post e junto as duas coisas numa receita. Costuma
                demorar mais que as outras — vale a espera.
              </p>
            </div>

            {mutation.isPending && <CookingLoader source="video" />}

            <form
              onSubmit={handleSubmitVideo}
              className="tile-drop flex flex-col gap-5"
              style={{ '--i': 2 } as CSSProperties}
            >
              <div className="flex flex-col gap-2">
                <label htmlFor="recipe-video-url" className={LABEL_CLASS}>
                  Link do vídeo
                </label>
                <MascotStage
                  room="mt-24"
                  pose={
                    !mutation.isPending && (
                      <MascotFilming className="mascot-lift pointer-events-none absolute right-0 bottom-full z-10 mb-[-9px] w-[186px]" />
                    )
                  }
                >
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
                </MascotStage>
              </div>
              <button
                type="submit"
                disabled={mutation.isPending || !isOnline}
                className={BUTTON_CLASS}
              >
                {mutation.isPending ? 'Assistindo o vídeo…' : 'Extrair do vídeo'}
              </button>
            </form>
          </>
        )}

        {open === 'link' && (
          <>
            <div className="tile-drop flex flex-col gap-2" style={{ '--i': 1 } as CSSProperties}>
              <h2 className="font-display text-[1.7rem] leading-[1.05] font-extrabold tracking-[-0.03em] text-ink">
                Tem o <span className="text-accent">link</span> da receita?
              </h2>
              <p className="text-sm leading-relaxed text-ink-muted">
                Cola aqui e deixa comigo. Eu leio a página inteira — inclusive a
                parte sobre a viagem da autora à Toscana — e trago só o que
                interessa.
              </p>
            </div>

            {mutation.isPending && <CookingLoader source="link" />}

            <form
              onSubmit={handleSubmitUrl}
              className="tile-drop flex flex-col gap-5"
              style={{ '--i': 2 } as CSSProperties}
            >
              <div className="flex flex-col gap-2">
                <label htmlFor="recipe-url" className={LABEL_CLASS}>
                  Link da receita
                </label>
                <MascotStage
                  room="mt-16"
                  pose={
                    !mutation.isPending && (
                      <MascotLounging className="mascot-lift pointer-events-none absolute right-0 bottom-full z-10 mb-[-10px] w-[190px]" />
                    )
                  }
                >
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
                </MascotStage>
              </div>
              <button
                type="submit"
                disabled={mutation.isPending || !isOnline}
                className={BUTTON_CLASS}
              >
                {mutation.isPending ? 'Extraindo receita…' : 'Adicionar receita'}
              </button>
            </form>
          </>
        )}

        {mutation.isError && (
          <p role="alert" className="border-l-4 border-accent pl-3 text-sm font-medium text-ink">
            {mutation.error.message}
          </p>
        )}
      </div>
    </div>
  )
}
