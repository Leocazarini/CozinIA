interface IconProps {
  className?: string
}

// Chunky line icons for the bottom nav — decorative only, the visible
// label text next to them already carries the accessible name. The heavy
// stroke matches the 2px tile borders used everywhere else.
const sharedProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.1,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  focusable: false,
}

export function BookIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <path d="M4 5.5C4 4.67 4.67 4 5.5 4H12v16H5.5A1.5 1.5 0 0 1 4 18.5v-13Z" />
      <path d="M20 5.5c0-.83-.67-1.5-1.5-1.5H12v16h6.5c.83 0 1.5-.67 1.5-1.5v-13Z" />
      <path d="M7.5 8.5h2M7.5 11.5h2" />
    </svg>
  )
}

export function PlusIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <path d="M12 5.5v13M5.5 12h13" />
    </svg>
  )
}

export function SunIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2.5v2.3M12 19.2v2.3M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.3M19.2 12h2.3M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6" />
    </svg>
  )
}

export function MoonIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <path d="M19.5 14.5a8 8 0 1 1-9-11 6.3 6.3 0 0 0 9 9Z" />
    </svg>
  )
}

/**
 * The three doors into a recipe, as tab marks. Drawn from the same chunky
 * strokes as the nav icons so the tab strip reads as painted, not imported:
 * a boxy camera with a bellows-era hump, a camcorder pointing right (the
 * same silhouette the mascot's tripod carries), and a chain link.
 */
export function CameraIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <path d="M5.5 8.4h2.6l1.5-2.3h4.8l1.5 2.3h2.6A1.5 1.5 0 0 1 20 9.9v7.6a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5V9.9a1.5 1.5 0 0 1 1.5-1.5Z" />
      <circle cx="12" cy="13.4" r="3.4" />
    </svg>
  )
}

export function VideoIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <rect x="2.6" y="6.8" width="12.8" height="10.4" rx="2" />
      <path d="M21.4 8.4 15.4 12l6 3.6V8.4Z" />
    </svg>
  )
}

export function LinkIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <path d="M10.2 13.2a4.2 4.2 0 0 0 6.1.3l2.6-2.6a4.2 4.2 0 0 0-5.9-5.9l-1.5 1.5" />
      <path d="M13.8 10.8a4.2 4.2 0 0 0-6.1-.3l-2.6 2.6a4.2 4.2 0 0 0 5.9 5.9l1.5-1.5" />
    </svg>
  )
}

export function SearchIcon({ className }: IconProps) {
  return (
    <svg className={className} {...sharedProps}>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M19.5 19.5l-4.35-4.35" />
    </svg>
  )
}

/**
 * The four-petal rosette at the centre of the azulejo tile, reused as a
 * standalone ornament to close panels and mark empty states.
 */
export function Quatrefoil({ className }: IconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M6 6 A6 6 0 0 1 18 6 A6 6 0 0 1 18 18 A6 6 0 0 1 6 18 A6 6 0 0 1 6 6 Z" />
      <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none" />
    </svg>
  )
}
