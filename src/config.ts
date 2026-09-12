// GitHub repo URL enables the "Editează pe GitHub" deep links.
export const REPO_URL = 'https://github.com/DynoW/ro-edu-registry'

// Base URL-aware data path (works both at '/' and under GitHub Pages sub-path).
export const dataUrl = (file: string): string => `${import.meta.env.BASE_URL}data/${file}`

export const ISSUE_TEMPLATES = {
  addEntity: 'add-entity.yml',
  fixData: 'fix-data.yml',
}
