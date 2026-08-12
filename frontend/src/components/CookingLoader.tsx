import { type CSSProperties, useEffect, useState } from 'react'
import { MascotCooking } from './Mascot'

/**
 * Extraction takes as long as it takes — an LLM reading a whole blog page.
 * A spinner would only say "something is happening"; naming the step the
 * mascot is actually on says *what*, which is what stops the wait from
 * reading as a freeze.
 */
const STEPS = [
  'Abrindo o link…',
  'Pulando a história da vovó…',
  'Separando os ingredientes…',
  'Anotando o modo de preparo…',
  'Conferindo tempos e porções…',
  'Provando o tempero…',
]

const STEP_MS = 2600

export function CookingLoader() {
  const [step, setStep] = useState(0)

  useEffect(() => {
    // Holds on the last step instead of looping: a caption that restarts
    // tells the user the request restarted, which is a lie.
    const timer = setInterval(() => {
      setStep((current) => Math.min(current + 1, STEPS.length - 1))
    }, STEP_MS)
    return () => clearInterval(timer)
  }, [])

  return (
    <div
      className="tile tile-keyline tile-drop flex flex-col items-center gap-4 px-5 py-6"
      style={{ '--i': 0 } as CSSProperties}
    >
      <MascotCooking className="h-24 w-24" />

      <p
        role="status"
        aria-live="polite"
        // `key` remounts the paragraph on every step so the fade replays.
        key={step}
        className="caption-fade text-center font-display text-base font-extrabold tracking-[-0.01em] text-ink"
      >
        {STEPS[step]}
      </p>

      {/* An azulejo rail rather than a progress bar: the wait is indefinite,
          so it paces the eye without pretending to know a percentage. */}
      <div className="flex gap-1.5" aria-hidden="true">
        {[0, 1, 2, 3, 4, 5].map((index) => (
          <span
            key={index}
            className="rail-pulse h-2.5 w-2.5 rounded-[2px] border-2 border-ink bg-accent"
            style={{ '--i': index } as CSSProperties}
          />
        ))}
      </div>

      <p className="max-w-[16rem] text-center text-xs leading-relaxed text-ink-muted">
        Pode levar uns segundos. Não feche a página — a panelinha está lendo.
      </p>
    </div>
  )
}
