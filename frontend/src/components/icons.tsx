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
