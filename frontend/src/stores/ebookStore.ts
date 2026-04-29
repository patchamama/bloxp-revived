import { create } from 'zustand'

interface StoreFields {
  feedUrl: string
  startingUrl: string
  startingTitle: string
  siteUrl: string
  siteTitle: string
  siteDescription: string
  maxPosts: number
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
  maxPosts: 250,
  customSearchOpt: false,
  tagName: '',
  attrName: '',
  attrValue: '',
  preString: '',
  parentTag: false,
  linksToFootnotes: false,
  addTOC: true,
  includeImages: true,
}

export const useEbookStore = create<EbookStore>((set) => ({
  ...defaults,
  activeJobId: null,
  setField: (key, value) => set({ [key]: value } as Partial<EbookStore>),
  setActiveJobId: (id) => set({ activeJobId: id }),
  reset: () => set({ ...defaults, activeJobId: null }),
}))
