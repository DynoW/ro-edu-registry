export type Kind =
  | 'school'
  | 'highschool'
  | 'robotics-club'
  | 'university'
  | 'faculty'
  | 'student-org'

export type CoordsPrecision = 'building' | 'address' | 'locality' | 'area'

export interface LinkRef {
  t: string
  v: string
  l?: string
  ok?: boolean
}

export interface EntityProps {
  id: string
  kind: Kind
  name: string
  county: string
  city?: string
  parent?: string
  external_ids?: Record<string, string | number>
  env?: string | null
  addr?: string | null
  postcode?: string | null
  cand?: number | null
  rep?: number | null
  nerep?: number | null
  coords_precision?: CoordsPrecision | null
  links?: LinkRef[]
}

export interface Feature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: EntityProps
}

export interface KindMeta {
  id: Kind
  label: string
  color: string
}

export const KINDS: KindMeta[] = [
  { id: 'school', label: 'Școli', color: '#f59e0b' },
  { id: 'highschool', label: 'Licee', color: '#0284c7' },
  { id: 'robotics-club', label: 'Cluburi robotică', color: '#ec4899' },
  { id: 'university', label: 'Universități', color: '#7c3aed' },
  { id: 'faculty', label: 'Facultăți', color: '#a78bfa' },
  { id: 'student-org', label: 'Asociații studenți', color: '#6366f1' },
]

export const KIND_META: Record<Kind, KindMeta> = Object.fromEntries(
  KINDS.map((k) => [k.id, k]),
) as Record<Kind, KindMeta>

export const KIND_SINGULAR: Record<Kind, string> = {
  school: 'Școală',
  highschool: 'Liceu',
  university: 'Universitate',
  faculty: 'Facultate',
  'robotics-club': 'Club robotică',
  'student-org': 'Asociație studențească',
}

export const isSchoolKind = (kind: Kind): boolean => kind === 'school' || kind === 'highschool'

export interface Coverage {
  generated: string
  total: {
    entities: number
    coords_pct: number
    website_pct: number
    email_pct: number
  }
  counties: Record<
    string,
    {
      entities: number
      coords_pct: number
      website_pct: number
      email_pct: number
    }
  >
}
