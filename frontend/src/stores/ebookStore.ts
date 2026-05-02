import { create } from 'zustand'

const MAX_POSTS_STORAGE_KEY = 'bloxp:max_posts_preference'

function clampMaxPosts(value: number): number {
  return Math.min(9999, Math.max(1, value))
}

function getInitialMaxPosts(): number {
  if (typeof window === 'undefined') return 250
  const raw = window.localStorage.getItem(MAX_POSTS_STORAGE_KEY)
  if (!raw) return 250
  const parsed = Number.parseInt(raw, 10)
  if (Number.isNaN(parsed)) return 250
  return clampMaxPosts(parsed)
}

interface StoreFields {
  feedUrl: string
  startingUrl: string
  startingTitle: string
  siteUrl: string
  siteTitle: string
  siteDescription: string
  maxPosts: number
  postRangeStart: number
  postRangeEnd: number
  customSearchOpt: boolean
  tagName: string
  attrName: string
  attrValue: string
  preString: string
  parentTag: boolean
  linksToFootnotes: boolean
  addTOC: boolean
  includeImages: boolean
}

interface EbookStore extends StoreFields {
  activeJobId: string | null
  setField: <K extends keyof StoreFields>(key: K, value: StoreFields[K]) => void
  saveMaxPostsPreference: () => void
  setActiveJobId: (id: string | null) => void
  reset: () => void
}

const defaults: StoreFields = {
  feedUrl: '',
  startingUrl: '',
  startingTitle: '',
  siteUrl: '',
  siteTitle: '',
  siteDescription: '',
  maxPosts: getInitialMaxPosts(),
  postRangeStart: 1,
  postRangeEnd: getInitialMaxPosts(),
  customSearchOpt: false,
  tagName: '',
  attrName: '',
  attrValue: '',
  preString: '',
  parentTag: false,
  linksToFootnotes: true,
  addTOC: true,
  includeImages: true,
}

export const useEbookStore = create<EbookStore>((set) => ({
  ...defaults,
  activeJobId: null,
  setField: (key, value) => set({ [key]: value } as Partial<EbookStore>),
  saveMaxPostsPreference: () =>
    set((state) => {
      const clamped = clampMaxPosts(state.maxPosts)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(MAX_POSTS_STORAGE_KEY, String(clamped))
      }
      return { maxPosts: clamped }
    }),
  setActiveJobId: (id) => set({ activeJobId: id }),
  reset: () => set({ ...defaults, activeJobId: null }),
}))
