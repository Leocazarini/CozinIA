import type { CSSProperties, ReactNode } from 'react'

interface MascotProps {
  className?: string
}

/**
 * The Panelinha — CozinIA's mascot. The logo's pot *is* the head: the solid
 * cobalt lid bar, the open bowl beneath it and the two urucum steam curls
 * are the icon from `design/icon-source.svg`, unchanged and deliberately
 * faceless. Under it hangs a plain line-art body in a flour-dusted apron.
 *
 * Every pose shares one canonical space, 120 units wide with the character
 * centred on x=60, and each helper takes the y it should sit at. Only the
 * limbs change between poses; the head and body are the same path data
 * everywhere, which is what keeps it one character across the app.
 */

const TILE = 'var(--color-tile)'
const SURFACE = 'var(--color-surface)'

/** Ceramic fill + cobalt keyline — the whole character is drawn in this. */
const inked = {
  fill: SURFACE,
  stroke: TILE,
  strokeWidth: 2.8,
  strokeLinejoin: 'round' as const,
  strokeLinecap: 'round' as const,
}

const stroked = { ...inked, fill: 'none' }

/**
 * An arm or leg. Drawn as one fat cobalt stroke with a thinner ceramic
 * stroke laid over it, which yields an outlined tube from a single path —
 * far less fragile than hand-authoring both edges as a closed shape.
 */
function Limb({ d }: { d: string }) {
  return (
    <>
      <path d={d} fill="none" stroke={TILE} strokeWidth="9.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} fill="none" stroke={SURFACE} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </>
  )
}

/**
 * The pot, as a head. `y` is the top of the lid bar; the bowl bottom always
 * lands at y+34.3. `curls` is how many steam waves to stack — raised arms
 * need the short version so the steam does not collide with them.
 */
function PotHead({
  y,
  curls,
  animateSteam = false,
  children,
}: {
  y: number
  curls: 2 | 3
  animateSteam?: boolean
  children?: ReactNode
}) {
  const wave = 'c-3.2 3 3.2 4.5 0 7.5'.concat('s3.2 4.5 0 7.5'.repeat(curls - 1))
  const top = y - 2 - curls * 7.5

  return (
    <>
      <g stroke="var(--color-accent)" strokeWidth="3.4" fill="none" strokeLinecap="round">
        {[0, 1].map((i) => (
          <path
            key={i}
            className={animateSteam ? 'steam-rise' : undefined}
            style={animateSteam ? ({ '--i': i } as CSSProperties) : undefined}
            d={`M${i === 0 ? 47.5 : 72.5} ${top + i * 2}${wave}`}
          />
        ))}
      </g>
      <path
        d={`M31.2 ${y + 5.5}A28.8 28.8 0 0 0 88.8 ${y + 5.5}Z`}
        fill={SURFACE}
        stroke={TILE}
        strokeWidth="3.4"
        strokeLinejoin="round"
      />
      {/* Sits inside the open bowl, above the lid bar that closes it off. */}
      {children}
      <rect x="20.2" y={y} width="79.6" height="5.5" rx="2.75" fill={TILE} />
    </>
  )
}

/** Shoulders down to the apron hem. `s` is the shoulder line. */
function Body({ s, hem, pocket = true }: { s: number; hem: number; pocket?: boolean }) {
  return (
    <>
      <path
        d={`M53 ${s}C45 ${s + 2} 39 ${s + 9} 37 ${s + 19}L36 ${hem - 5}Q36 ${hem} 41 ${hem}L79 ${hem}Q84 ${hem} 84 ${hem - 5}L83 ${s + 19}C81 ${s + 9} 75 ${s + 2} 67 ${s}Z`}
        {...inked}
      />
      {/* Apron straps crossing the chest, and the bib's top edge. */}
      <path d={`M54 ${s + 1}L47 ${s + 9}M66 ${s + 1}L73 ${s + 9}M47 ${s + 9}L73 ${s + 9}`} {...stroked} />
      {pocket && (
        <path
          d={`M46 ${hem - 24}L74 ${hem - 24}L74 ${hem - 15}Q74 ${hem - 12} 71 ${hem - 12}L49 ${hem - 12}Q46 ${hem - 12} 46 ${hem - 15}Z`}
          {...inked}
        />
      )}
    </>
  )
}

function Legs({ top, splay = 3 }: { top: number; splay?: number }) {
  return (
    <>
      <rect x="44" y={top} width="14" height="20" rx="6" {...inked} />
      <rect x="62" y={top} width="14" height="20" rx="6" {...inked} />
      <ellipse cx={44 - splay} cy={top + 19} rx="11" ry="5.5" {...inked} />
      <ellipse cx={76 + splay} cy={top + 19} rx="11" ry="5.5" {...inked} />
    </>
  )
}

/** Flour caught on the apron. Positions are per-pose, in canonical units. */
function Flour({ spots }: { spots: [number, number, number][] }) {
  return (
    <g fill="var(--color-line)">
      {spots.map(([cx, cy, r]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} />
      ))}
    </g>
  )
}

/** Little cobalt ticks, the comic shorthand for movement. */
function Ticks({ x, y, flip = 1 }: { x: number; y: number; flip?: number }) {
  return (
    <g {...stroked}>
      {([[0, 0, 4.5, -4.5], [6, -4.5, 2, -5], [4, 5, 5, 1.5]] as const).map(([a, b, c, d]) => (
        <path key={a + b} d={`M${x + flip * a} ${y + b}l${flip * c} ${d}`} />
      ))}
    </g>
  )
}

/**
 * Pose one: hung off the header's bottom rule by both mitts, dangling over
 * the recipe list. The arms swing wide *around* the pot rather than beside
 * it — routed close in, they traced the bowl's own curve and read as a
 * halo instead of arms. Limbs are drawn before the head so their ends
 * disappear behind it.
 */
export function MascotHanging({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 0 120 148" fill="none" aria-hidden="true" focusable="false">
      <g className="mascot-sway">
        <Limb d="M27 17C21 32 21 52 27 63C32 72 40 76 50 77" />
        <Limb d="M93 17C99 32 99 52 93 63C88 72 80 76 70 77" />
        {/* The mitts straddle y≈11, where the header's own border-bottom
            passes through them — the rule the page already draws is what
            they appear to grip. */}
        <rect x="20.5" y="4" width="13" height="14" rx="6.5" {...inked} />
        <rect x="86.5" y="4" width="13" height="14" rx="6.5" {...inked} />
        <Body s={74} hem={126} />
        <Legs top={124} />
        <Flour spots={[[57, 90, 1.6], [68, 86, 2], [51, 108, 1.3], [71, 104, 1.5], [58, 120, 1.8], [47, 135, 1.1]]} />
        <PotHead y={28} curls={2} />
      </g>
    </svg>
  )
}

/**
 * Pose two: draped over the top edge of the URL field, forearms folded on
 * it. The forearms straddle y=74 and the ~18 units below that are meant to
 * overlap the field itself — see the positioning in AddRecipe.
 */
export function MascotLeaning({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 -20 120 112" fill="none" aria-hidden="true" focusable="false">
      <g className="mascot-lean">
        <Limb d="M50 50C45 56 43 64 43 71" />
        <Limb d="M70 50C75 56 77 64 77 71" />
        {/* A wider, squatter chest than `Body` gives — only a sliver of torso
            shows between bowl and forearms here, and the tapered version
            turned the whole silhouette into an hourglass. */}
        <path d="M47 46C39 50 35 58 34 72L86 72C85 58 81 50 73 46Z" {...inked} />
        <path d="M54 47L46 56M66 47L74 56M46 56L74 56" {...stroked} />
        <Flour spots={[[58, 62, 1.6], [70, 60, 1.9], [48, 68, 1.2]]} />
        <PotHead y={12} curls={3} />
        {/* Two forearms crossed on the edge, each tilted off the horizontal
            and capped with a fist at its outer end. */}
        <g transform="rotate(-3 60 74)">
          <rect x="29" y="68" width="47" height="12" rx="6" {...inked} />
          <circle cx="32" cy="74" r="5.8" {...inked} />
        </g>
        <g transform="rotate(2.5 60 77)">
          <rect x="45" y="71" width="46" height="12" rx="6" {...inked} />
          <circle cx="88" cy="77" r="5.8" {...inked} />
        </g>
      </g>
    </svg>
  )
}

const BUBBLES: [number, number, number][] = [
  [50, 40, 2.6],
  [60, 44, 3.2],
  [70, 40, 2.3],
]

/**
 * Pose three: at work. Head and apron only, with steam actually leaving the
 * pot on a loop and something bubbling in the bowl. Anchors the extraction
 * loader, where the whole job is proving the app is still awake.
 */
export function MascotCooking({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="8 -8 104 104" fill="none" aria-hidden="true" focusable="false">
      <Body s={46} hem={94} />
      <Flour spots={[[57, 62, 1.6], [69, 58, 1.9], [52, 84, 1.3]]} />
      <PotHead y={18} curls={3} animateSteam>
        <g fill={TILE} opacity="0.45">
          {BUBBLES.map(([cx, cy, r], i) => (
            <circle
              key={cx}
              className="bubble-up"
              style={{ '--i': i } as CSSProperties}
              cx={cx}
              cy={cy}
              r={r}
            />
          ))}
        </g>
      </PotHead>
      <Ticks x={16} y={30} flip={-1} />
      <Ticks x={104} y={34} />
    </svg>
  )
}
