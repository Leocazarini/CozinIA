import type { CSSProperties, ReactNode } from 'react'

interface MascotProps {
  className?: string
}

/**
 * The Panelinha — CozinIA's mascot. The logo's pot *is* the head: the solid
 * cobalt lid bar, the open bowl beneath it and the two urucum steam curls
 * are the icon from `design/icon-source.svg`, unchanged and deliberately
 * faceless. Under it hangs a line-art body in a flour-dusted apron, with
 * proper Haring-style hands, chunky boots and an apron bow on the back.
 *
 * Every pose shares one canonical convention: y=0 is the TOP of the ruled
 * line the mascot interacts with (the header's bottom border on Home, the
 * URL field's top border on AddRecipe). Everything above the line is
 * negative y, which is what lets the page CSS position each pose against
 * the real border with plain pixel math.
 */

const TILE = 'var(--color-tile)'
const SURFACE = 'var(--color-surface)'

const inked = {
  fill: SURFACE,
  stroke: TILE,
  strokeWidth: 2.8,
  strokeLinejoin: 'round' as const,
  strokeLinecap: 'round' as const,
}

const stroked = { ...inked, fill: 'none' }

/**
 * An arm or leg: one fat cobalt stroke with a thinner ceramic stroke laid
 * over it, yielding an outlined tube from a single path.
 */
function Limb({ d }: { d: string }) {
  return (
    <>
      <path d={d} fill="none" stroke={TILE} strokeWidth="9.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} fill="none" stroke={SURFACE} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </>
  )
}

const SHORT_WAVE = 'c-3.2 3 3.2 4.5 0 7.5s3.2 4.5 0 7.5'
const FULL_WAVE = `${SHORT_WAVE}s3.2 4.5 0 7.5`

/**
 * The two steam curls, animated: a faint solid curl keeps the logo's
 * silhouette present at all times, and a dashed copy of the same path
 * crawls upward along it (`steam-flow` shifts stroke-dashoffset), so the
 * smoke visibly travels *along the wave's own shape* rather than just
 * translating. The right curl starts lower and half a beat later so the
 * pair never reads as mirrored.
 */
function Steam({ cx, lidY, short = false }: { cx: number; lidY: number; short?: boolean }) {
  const wave = short ? SHORT_WAVE : FULL_WAVE
  const height = short ? 15 : 22.5
  return (
    <g stroke="var(--color-accent)" strokeWidth="3.4" fill="none" strokeLinecap="round">
      {[0, 1].map((i) => {
        const d = `M${cx + (i === 0 ? -12.5 : 12.5)} ${lidY - 2 - height + i * 2}${wave}`
        return (
          <g key={i}>
            <path d={d} opacity="0.3" />
            <path className="steam-flow" style={{ animationDelay: `${i * 0.4}s` }} d={d} />
          </g>
        )
      })}
    </g>
  )
}

/**
 * The pot, as a head. `lidY` is the top of the lid bar; the bowl bottom
 * always lands at lidY+34.3. A non-zero `tilt` pitches the whole head —
 * steam included — around the neck, which is how every pose "looks down"
 * at whatever sits below it.
 */
function PotHead({
  cx,
  lidY,
  tilt = 0,
  shortSteam = false,
  children,
}: {
  cx: number
  lidY: number
  tilt?: number
  shortSteam?: boolean
  children?: ReactNode
}) {
  const lidBottom = lidY + 5.5
  const inner = (
    <>
      <Steam cx={cx} lidY={lidY} short={shortSteam} />
      <path
        d={`M${cx - 28.8} ${lidBottom}A28.8 28.8 0 0 0 ${cx + 28.8} ${lidBottom}Z`}
        fill={SURFACE}
        stroke={TILE}
        strokeWidth="3.4"
        strokeLinejoin="round"
      />
      {/* Sits inside the open bowl, above the lid bar that closes it. */}
      {children}
      <rect x={cx - 39.8} y={lidY} width="79.6" height="5.5" rx="2.75" fill={TILE} />
    </>
  )
  return tilt !== 0 ? <g transform={`rotate(${tilt} ${cx} ${lidY + 36})`}>{inner}</g> : <>{inner}</>
}

/**
 * An open hand, Haring-style: four splayed fingers and a thumb as one
 * filled silhouette. Authored pointing up with the wrist at the local
 * origin; place it with translate/rotate/scale.
 */
function OpenHand({ x, y, rotate = 0, scale = 1 }: { x: number; y: number; rotate?: number; scale?: number }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate}) scale(${scale})`}>
      <path
        d="M -5 0.5 C -6.6 -2.4 -7.2 -5.6 -6.6 -8.4
           C -7.8 -9 -9.6 -10.4 -10.2 -12.6 C -10.8 -14.9 -9.2 -16.1 -7.6 -14.9
           C -6.6 -14.1 -5.6 -12.9 -4.9 -11.7
           C -5.4 -14.3 -5.1 -17.3 -4.1 -19.5 C -3.2 -21.6 -1.4 -21.2 -1.5 -18.9
           C -1.55 -16.9 -1.7 -14 -1.8 -11.8
           C -1.1 -14.8 -0.5 -18.4 0.6 -20.6 C 1.7 -22.8 3.4 -22.2 3.2 -19.8
           C 3.05 -17.6 2.6 -14.2 2.3 -11.9
           C 3 -14.3 3.7 -17.2 4.8 -18.8 C 6 -20.5 7.6 -19.7 7.2 -17.6
           C 6.9 -15.9 6.3 -13.2 5.8 -11.2
           C 6.6 -12.6 7.4 -13.9 8.4 -14.7 C 9.9 -15.9 11 -14.6 10.3 -12.8
           C 9.5 -10.7 8.2 -8.9 6.9 -7.6 C 7.2 -4.8 6.6 -2 5.4 0.4 Z"
        fill={SURFACE}
        stroke={TILE}
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
    </g>
  )
}

/**
 * A hand lying flat, seen from above: a rounded mitt with three finger
 * separations. Authored pointing left with the wrist at the local origin.
 */
function FlatHand({
  x,
  y,
  rotate = 0,
  flip = false,
  scale = 1,
}: {
  x: number
  y: number
  rotate?: number
  flip?: boolean
  scale?: number
}) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate}) scale(${(flip ? -1 : 1) * scale} ${scale})`}>
      <path
        d="M 0 -7.2 C -5 -7.8 -10.5 -7.6 -13.6 -6.4
           C -16.2 -5.4 -16.4 -1.8 -13.8 -0.9 C -10.8 0.1 -5 0.2 0 -0.3 Z"
        {...inked}
      />
      <path
        d="M-4.6 -6.8 L-5 -0.4 M-8.4 -7 L-8.8 -0.5 M-11.8 -6.2 L-12.1 -1"
        fill="none"
        stroke={TILE}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </g>
  )
}

/** A chunky rounded boot. Authored toe-left with the ankle at the origin. */
function Boot({ x, y, rotate = 0, flip = false }: { x: number; y: number; rotate?: number; flip?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate}) scale(${flip ? -1 : 1} 1)`}>
      <path
        d="M -1.6 -5 C -6.4 -5.4 -10.4 -3 -10.9 0.2 C -11.3 3.1 -8.2 4.6 -4.4 4.6
           L 3.8 4.6 C 6.4 4.6 7.1 2.8 6.4 0.6 L 5.2 -4.6 C 3 -5.2 0.6 -5.2 -1.6 -5 Z"
        {...inked}
      />
    </g>
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
 * Pose one — Home. Lying belly-down along the header's bottom rule like a
 * kid on a wall: forearm folded on the line, head hanging over the edge
 * tilted down at the recipe list, hips curving over the "beam" with the
 * apron bow on the back, and the lower legs dangling on the far side.
 *
 * The behind-the-line illusion is a transparent window in the artwork:
 * nothing is drawn between y=0 and y=9.5, and the page positions the SVG
 * so the header's real 2px border and 6px frieze show through exactly
 * there — the legs resume below it, visibly "behind" the line. That is
 * also why this pose must stay compact above the line: the header is only
 * ~58px tall, and anything taller would poke out of the viewport.
 */
export function MascotPerched({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 -66 140 99" fill="none" aria-hidden="true" focusable="false">
      <g className="legs-dangle">
        <Limb d="M100 9.5 C99 15 97.5 20 95.5 24.5" />
        <Boot x={91} y={26} />
        <Limb d="M111 9.5 C111.5 14 112 18 113 21.5" />
        <Boot x={116} y={23} rotate={8} flip />
        <Flour spots={[[98, 17, 1.1]]} />
      </g>

      <g className="mascot-breathe">
        {/* Back and hip, resting on the line. */}
        <path
          d="M58 -22 C74 -26 90 -24 99 -17 C105 -12 106.5 -6 104.5 -1.5 L58 -1.5 C54 -8 54 -16 58 -22 Z"
          {...inked}
        />
        {/* Apron strap across the back, tied in a bow at the hip. */}
        <path d="M64 -21.5 C74 -24.5 85 -23.6 93 -20.4" fill="none" stroke={TILE} strokeWidth="2" strokeLinecap="round" />
        <path d="M95 -20.5 C91 -26 85.5 -24 88.5 -19.6 C90 -17.6 92.8 -18.2 95 -20.5 Z" {...inked} />
        <path d="M95 -20.5 C99 -26 104.5 -24 101.5 -19.6 C100 -17.6 97.2 -18.2 95 -20.5 Z" {...inked} />
        <path
          d="M93.5 -19 C92.5 -15 91 -12 88.5 -10 M97 -19 C97.5 -15 98.5 -12 100.5 -9.5"
          fill="none"
          stroke={TILE}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <Flour spots={[[72, -14, 1.5], [88, -9, 1.2], [63, -7, 1]]} />

        {/* The elbow-prop: forearm folded flat along the line. */}
        <Limb d="M56 -4.5 C48 -5.5 40 -5.5 31 -4.8" />
        <FlatHand x={28.5} y={-1.2} />

        <PotHead cx={48} lidY={-47.3} tilt={-15} shortSteam />
      </g>
    </svg>
  )
}

/**
 * Pose two — AddRecipe. Lounging on the top edge of the URL field: lying
 * on one side, head propped on an open hand (elbow planted on the field's
 * rule), the other hand resting on the hip, ankles crossed at the far end.
 * The whole body sits on y≈-2, so its lower contour hugs the field's own
 * 2px border and it reads as lying on the input, not floating near it.
 */
export function MascotLounging({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 -88 210 96" fill="none" aria-hidden="true" focusable="false">
      <g className="mascot-breathe">
        {/* Neck stub, mostly hidden behind the bowl. */}
        <path d="M66 -34 L64 -22 L78 -22 L76 -32 Z" {...inked} />
        {/* Torso lying along the line, belly slumped onto it. */}
        <path
          d="M76 -31 C92 -34.5 128 -34.5 141 -29 C149.5 -25.5 152 -17 149 -9.5 C147 -4.5 141 -2.6 133 -2.6 L90 -2.6 C80 -2.6 75.5 -9 75.5 -17 C75.5 -23 75.6 -27 76 -31 Z"
          {...inked}
        />
        {/* Apron: hem line, tilted pocket, bib edge and straps. */}
        <path d="M124 -33 C125.5 -23 126.5 -13 127 -3" {...stroked} />
        <g transform="rotate(3 106 -17)">
          <path d="M96 -24 L120 -24 L120 -13 Q120 -10 117 -10 L99 -10 Q96 -10 96 -13 Z" {...inked} />
        </g>
        <path d="M84 -25 C92 -27 100 -27.2 108 -26.5 M86 -29.5 L89 -25 M101 -30.5 L104 -26" {...stroked} />
        <Flour spots={[[90, -8, 1.5], [112, -28, 1.2], [134, -9, 1.6], [86, -15, 1], [142, -20, 1.2]]} />

        {/* Legs: ankles crossed, the upper boot resting over the lower. */}
        <Limb d="M143 -16 C154 -16 166 -15.5 176 -13.5" />
        <Boot x={182} y={-15} rotate={-14} flip />
        <Limb d="M146 -12 C158 -11.5 170 -10 180 -8" />
        <Boot x={187} y={-4.8} rotate={8} flip />

        {/* Free arm draped over the hip. */}
        <Limb d="M86 -29 C94 -26 102 -24.5 110 -25.5" />
        <FlatHand x={115} y={-23.5} rotate={-10} flip scale={0.95} />

        <PotHead cx={52} lidY={-58} tilt={-14} />

        {/* The prop: elbow on the line, open hand cradling the bowl's rim. */}
        <Limb d="M15 -1.5 C12.5 -10 14 -19 19 -25" />
        <OpenHand x={20} y={-27} rotate={-40} scale={0.9} />
      </g>
    </svg>
  )
}

/** Shoulders down to the apron hem — used by the cooking pose. */
function Body({ s, hem }: { s: number; hem: number }) {
  return (
    <>
      <path
        d={`M53 ${s}C45 ${s + 2} 39 ${s + 9} 37 ${s + 19}L36 ${hem - 5}Q36 ${hem} 41 ${hem}L79 ${hem}Q84 ${hem} 84 ${hem - 5}L83 ${s + 19}C81 ${s + 9} 75 ${s + 2} 67 ${s}Z`}
        {...inked}
      />
      <path d={`M54 ${s + 1}L47 ${s + 9}M66 ${s + 1}L73 ${s + 9}M47 ${s + 9}L73 ${s + 9}`} {...stroked} />
      <path
        d={`M46 ${hem - 24}L74 ${hem - 24}L74 ${hem - 15}Q74 ${hem - 12} 71 ${hem - 12}L49 ${hem - 12}Q46 ${hem - 12} 46 ${hem - 15}Z`}
        {...inked}
      />
    </>
  )
}

const BUBBLES: [number, number, number][] = [
  [50, 40, 2.6],
  [60, 44, 3.2],
  [70, 40, 2.3],
]

/**
 * Pose three — the extraction loader. Head and apron only, steam flowing
 * and something bubbling in the bowl: the whole job of this pose is
 * proving the app is still awake.
 */
export function MascotCooking({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="8 -8 104 104" fill="none" aria-hidden="true" focusable="false">
      <Body s={46} hem={94} />
      <Flour spots={[[57, 62, 1.6], [69, 58, 1.9], [52, 84, 1.3]]} />
      <PotHead cx={60} lidY={18}>
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
