import { LinkRef } from '../types'

const TYPE_LABEL: Record<string, string> = {
  website: 'website',
  facebook: 'Facebook',
  instagram: 'Instagram',
  youtube: 'YouTube',
  linkedin: 'LinkedIn',
  discord: 'Discord',
  whatsapp: 'WhatsApp',
  tiktok: 'TikTok',
  email: 'email',
  phone: 'telefon',
  other: 'link',
}

const PARENT_LABEL: Partial<Record<string, string>> = {
  faculty: 'Facultate a',
  'robotics-club': 'Găzduit de',
  'student-org': 'Legată de',
}

export const parentLabel = (kind: string): string => PARENT_LABEL[kind] ?? 'Parte din'

const EXT_ID_LABEL: Record<string, string> = {
  ftc: 'Echipă FIRST Tech Challenge',
  fll: 'Echipă FIRST LEGO League',
  frc: 'Echipă FIRST Robotics Competition',
  vex: 'Echipă VEX Robotics',
}

export const extIdLabel = (key: string): string => EXT_ID_LABEL[key] ?? key

export function LinkChips({ links }: { links?: LinkRef[] }) {
  if (!links?.length) return null
  return (
    <div className="mt-3 flex flex-wrap gap-1.5 text-sm">
      {links.map((l, i) => {
        const href = l.t === 'email' ? `mailto:${l.v}` : l.t === 'phone' ? `tel:${l.v}` : l.v
        const external = l.t !== 'email' && l.t !== 'phone'
        const cls =
          l.t === 'email'
            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            : l.t === 'phone'
              ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              : 'bg-sky-50 text-sky-700 hover:bg-sky-100'
        return (
          <a
            key={i}
            href={href}
            target={external ? '_blank' : undefined}
            rel={external ? 'noreferrer' : undefined}
            className={`rounded-lg px-2 py-1 font-medium ${cls}`}
          >
            {l.l ?? (l.t === 'email' ? l.v : TYPE_LABEL[l.t] ?? l.t)}
          </a>
        )
      })}
    </div>
  )
}
