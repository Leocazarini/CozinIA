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
 * over it, yielding an outlined tube from a single path. `width` exists for
 * the objects built from that same tube at a thinner gauge — tripod legs, a
 * spoon handle.
 */
function Limb({ d, width = 9.6 }: { d: string; width?: number }) {
  return (
    <>
      <path d={d} fill="none" stroke={TILE} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" />
      <path
        d={d}
        fill="none"
        stroke={SURFACE}
        strokeWidth={width * 0.42}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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
 * Pose one — Home. Hanging off the header's bottom rule: both forearms
 * hooked over the line, the pot resting on it and tipped down at the
 * recipe list, and the whole body swinging underneath with the legs
 * kicking — someone who slipped and has not fallen yet.
 *
 * The behind-the-line illusion is a transparent window in the artwork:
 * nothing is drawn between y=0 and y=9.5, and the page positions the SVG
 * so the header's real 2px border and 6px frieze show through exactly
 * there. The neck and both shoulders live in that gap, which is what lets
 * the body read as hanging *from* the line rather than being glued to it.
 * That is also why the head has to stay compact above it: the header is
 * only ~58px tall, and anything taller would poke out of the viewport.
 */
export function MascotDangling({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 -54 120 131" fill="none" aria-hidden="true" focusable="false">
      {/* Everything below the line swings from where it hangs. */}
      <g className="body-swing">
        {/* Widest at the hem instead of tapering to shoulders the way the
            standing torso does: the shoulders are behind the rule, so what
            hangs below the line is the apron, its straps running up and
            vanishing into the gap. Tapered here, it would read as a sack
            on a hook. */}
        <path d="M38 10C36 24 34 38 33 49Q33 54 38 54L82 54Q87 54 87 49C86 38 84 24 82 10Z" {...inked} />
        <path d="M46 10L48 24M74 10L72 24" {...stroked} />
        <path d="M46 30L74 30L74 39Q74 42 71 42L49 42Q46 42 46 39Z" {...inked} />
        <Flour spots={[[41, 26, 1.5], [78, 35, 1.2], [60, 47, 1.1], [79, 18, 1]]} />
        {/* One leg kicking out, one drawn up — the difference is what says
            the fall is being fought rather than accepted. */}
        <g className="legs-dangle">
          <Limb d="M52 51C49 58 47 64 46 69" />
          <Boot x={44} y={71} />
          <Limb d="M68 51C73 56 75 61 72 65" />
          <Boot x={70} y={67} rotate={22} flip />
        </g>
      </g>

      {/* Forearms first so the pot covers where they meet the shoulders. */}
      <Limb d="M52 -3C42 -8 32 -8 24 -5" />
      <FlatHand x={23} y={-2} rotate={7} />
      <Limb d="M68 -3C78 -8 88 -8 96 -5" />
      <FlatHand x={97} y={-2} rotate={-7} flip />

      <PotHead cx={60} lidY={-36} tilt={-10} shortSteam />
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

/**
 * Shoulders down to the apron hem. Authored around x=60 — the axis the pot
 * head sits on in the cooking pose — and shifted by `cx` for poses that
 * stand somewhere else on the line.
 */
function Body({ s, hem, cx = 60 }: { s: number; hem: number; cx?: number }) {
  return (
    <g transform={cx === 60 ? undefined : `translate(${cx - 60} 0)`}>
      <path
        d={`M53 ${s}C45 ${s + 2} 39 ${s + 9} 37 ${s + 19}L36 ${hem - 5}Q36 ${hem} 41 ${hem}L79 ${hem}Q84 ${hem} 84 ${hem - 5}L83 ${s + 19}C81 ${s + 9} 75 ${s + 2} 67 ${s}Z`}
        {...inked}
      />
      <path d={`M54 ${s + 1}L47 ${s + 9}M66 ${s + 1}L73 ${s + 9}M47 ${s + 9}L73 ${s + 9}`} {...stroked} />
      <path
        d={`M46 ${hem - 24}L74 ${hem - 24}L74 ${hem - 15}Q74 ${hem - 12} 71 ${hem - 12}L49 ${hem - 12}Q46 ${hem - 12} 46 ${hem - 15}Z`}
        {...inked}
      />
    </g>
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

/**
 * The standing legs shared by the two upright poses: knees soft, feet
 * splayed, soles landing a hair below y=0 so the boots sit *on* the ruled
 * line rather than hovering over it. `cx` is the figure's axis.
 */
function StandingLegs({ cx, hem }: { cx: number; hem: number }) {
  return (
    <>
      <Limb d={`M${cx - 8} ${hem - 2}C${cx - 9} ${hem + 6} ${cx - 11} ${hem + 13} ${cx - 12} ${hem + 19}`} />
      <Boot x={cx - 14} y={-4} />
      <Limb d={`M${cx + 8} ${hem - 2}C${cx + 9} ${hem + 6} ${cx + 11} ${hem + 13} ${cx + 12} ${hem + 19}`} />
      <Boot x={cx + 14} y={-4} flip />
    </>
  )
}

/**
 * The camera from the era when you had to hold it against your face: body,
 * viewfinder hump, wind knob, and a bulb flash out on its bracket. The
 * shutter sits dead centre of the body, where a real one does. Its right
 * edge presses into the bowl — the mascot has no eye to raise it to, so the
 * pot's open face is where it goes. Authored around its own centre so the
 * caller can aim the whole thing with one rotation.
 */
function VintageCamera({ x, y, angle }: { x: number; y: number; angle: number }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${angle})`}>
      {/* Bulb flash on its bracket, and the burst it throws. */}
      <path d="M-15 -7h-9v-4" {...stroked} strokeWidth="2.4" />
      <circle cx="-24" cy="-15" r="4.8" {...inked} />
      <g className="flash-pop" stroke="var(--color-accent)" strokeWidth="2.8" strokeLinecap="round">
        {[-180, -142, -100, -55, 152].map((degrees) => {
          const radians = (degrees * Math.PI) / 180
          return (
            <path
              key={degrees}
              d={`M${-24 + Math.cos(radians) * 8.5} ${-15 + Math.sin(radians) * 8.5}l${Math.cos(radians) * 6.5} ${Math.sin(radians) * 6.5}`}
            />
          )
        })}
      </g>

      <rect x="-15" y="-11" width="30" height="22" rx="3" {...inked} />
      <rect x="-4" y="-16.5" width="13" height="6" rx="2" {...inked} />
      <circle cx="10" cy="-14" r="3" {...inked} />
      {/* Dead centre of the body, where a shutter actually sits. */}
      <circle cx="0" cy="0" r="7.6" {...inked} />
      <circle cx="0" cy="0" r="3.6" fill={TILE} opacity="0.45" />
      <circle cx="-2.4" cy="-1.6" r="1.4" fill={SURFACE} />
    </g>
  )
}

/**
 * The crew: a movie camera with two film reels on a tripod, its lens
 * pointing right at whoever is cooking. The tally light blinks, because a
 * camera that is not recording is just furniture.
 */
function FilmRig({ cx }: { cx: number }) {
  return (
    <g>
      <Limb width={7} d={`M${cx} -54C${cx - 13} -38 ${cx - 26} -16 ${cx - 32} -1`} />
      <Limb width={7} d={`M${cx} -54C${cx + 13} -38 ${cx + 26} -16 ${cx + 32} -1`} />
      <Limb width={5.6} d={`M${cx} -54C${cx + 2} -38 ${cx + 4} -20 ${cx + 5} -9`} />
      <path d={`M${cx - 17} -26h34`} {...stroked} strokeWidth="2.4" />

      {/* Tipped a few degrees toward the pot: the camera is framing a shot,
          not sitting in a shop window. */}
      <g transform={`rotate(5 ${cx} -54)`}>
        <circle cx={cx - 12} cy={-96} r="10" {...inked} />
        <circle cx={cx - 12} cy={-96} r="2.6" fill={TILE} />
        <circle cx={cx + 13} cy={-96} r="10" {...inked} />
        <circle cx={cx + 13} cy={-96} r="2.6" fill={TILE} />

        <rect x={cx - 26} y={-88} width="52" height="32" rx="3.5" {...inked} />
        {/* Lens barrel and hood, aimed at the cook. */}
        <rect x={cx + 24} y={-79} width="11" height="14" rx="2" {...inked} />
        <circle cx={cx + 41} cy={-72} r="7.2" {...inked} />
        <circle cx={cx + 41} cy={-72} r="3.2" fill={TILE} opacity="0.45" />
        {/* Crank on the far side, and the tally light. */}
        <circle cx={cx - 30} cy={-72} r="3.4" {...inked} />
        <path d={`M${cx - 30} -72l-6 -5`} {...stroked} strokeWidth="2.6" />
        <circle className="rec-blink" cx={cx + 17} cy={-82} r="3.4" fill="var(--color-accent)" />
      </g>
    </g>
  )
}

/**
 * A pot standing on the line, distinct from the one the mascot wears: a
 * belly that tapers to its base, a rolled rim, two ears, and the same steam
 * curls the logo uses.
 */
function StovePot({ cx }: { cx: number }) {
  return (
    <g>
      <Steam cx={cx} lidY={-36} short />
      <path d={`M${cx - 20} -30c-8 0-8 11 0 11`} {...stroked} strokeWidth="3" />
      <path d={`M${cx + 20} -30c8 0 8 11 0 11`} {...stroked} strokeWidth="3" />
      <path
        d={`M${cx - 24} -30L${cx - 18} -3Q${cx - 17} 0 ${cx - 14} 0L${cx + 14} 0Q${cx + 17} 0 ${cx + 18} -3L${cx + 24} -30Z`}
        {...inked}
      />
      <rect x={cx - 28} y={-36} width="56" height="7" rx="3.5" {...inked} />
    </g>
  )
}

/**
 * Pose four — the Imagem door. Standing on the field's top edge, leaning
 * into the shot, an old camera held up against the bowl and the flash going
 * off down into the field. The pot *is* the head, so pressing the camera
 * against its open face is this mascot's version of raising it to the eye.
 */
export function MascotSnapping({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="4 -124 100 132" fill="none" aria-hidden="true" focusable="false">
      <StandingLegs cx={62} hem={-26} />
      <g className="mascot-breathe">
        {/* The lean into the shot, pivoting at the hips. */}
        <g transform="rotate(-5 62 -26)">
          <Body s={-74} hem={-26} cx={62} />
          <Flour spots={[[46, -38, 1.5], [78, -33, 1.2], [68, -49, 1.1]]} />
          {/* Head first, then the camera over its left edge: the bowl keeps
              two thirds of its silhouette, which is the one thing that has
              to survive at this size. */}
          <PotHead cx={62} lidY={-102} tilt={-9} shortSteam />
          {/* Far arm hangs; the near one reaches up under the lens barrel
              and cradles it. Two arms on the camera read as one thick blob
              at the size this is actually drawn at. */}
          <Limb d="M74 -62C83 -58 85 -49 82 -42" />
          <FlatHand x={84} y={-39} rotate={-76} scale={0.88} />
          <VintageCamera x={48} y={-82} angle={-14} />
          <Limb d="M50 -62C42 -63 34 -65 29 -68" />
          <FlatHand x={30} y={-66} rotate={-52} flip scale={0.84} />
        </g>
      </g>
    </svg>
  )
}

/**
 * Pose five — the Vídeo door. A whole little set standing on the field's
 * top edge: the mascot stirring a pot on the counter while a movie camera
 * on a tripod films the take from the left.
 */
export function MascotFilming({ className }: MascotProps) {
  return (
    <svg className={className} viewBox="0 -124 216 132" fill="none" aria-hidden="true" focusable="false">
      <FilmRig cx={52} />

      <StandingLegs cx={162} hem={-26} />
      <g className="mascot-breathe">
        {/* Leaning over the pot, which is what stirring actually looks like. */}
        <g transform="rotate(-5 162 -26)">
          <Body s={-74} hem={-26} cx={162} />
          <Flour spots={[[146, -38, 1.5], [178, -33, 1.2], [168, -49, 1.1]]} />
          {/* Far arm hanging at the side. */}
          <Limb d="M176 -63C187 -58 189 -48 186 -40" />
          <FlatHand x={188} y={-37} rotate={-78} scale={0.9} />
          <PotHead cx={162} lidY={-102} tilt={9} shortSteam />
          {/* Stirring arm, and the spoon it drives into the pot — the
              handle stands well clear of the rim so the gesture is legible
              even though everything below the rim is hidden. */}
          <g className="stir">
            <Limb d="M150 -62C144 -58 138 -55 133 -53" />
            <Limb width={5.4} d="M136 -62L108 -26" />
            <FlatHand x={133} y={-53} rotate={-52} scale={0.9} />
          </g>
        </g>
      </g>

      <StovePot cx={118} />
    </svg>
  )
}
