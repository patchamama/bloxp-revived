import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { submitBasicJob, submitAdvancedJob } from '@/api/client'
import { useEbookStore } from '@/stores/ebookStore'

export function useSubmitBasicJob() {
  const navigate = useNavigate()
  const { feedUrl, linksToFootnotes, addTOC, includeImages, setActiveJobId } = useEbookStore()

  return useMutation({
    mutationFn: () =>
      submitBasicJob({
        feed_url: feedUrl,
        links_to_footnotes: linksToFootnotes,
        add_toc: addTOC,
        include_images: includeImages,
      }),
    onSuccess: ({ job_id }) => {
      setActiveJobId(job_id)
      navigate(`/working/${job_id}`)
    },
  })
}

export function useSubmitAdvancedJob() {
  const navigate = useNavigate()
  const store = useEbookStore()

  return useMutation({
    mutationFn: () =>
      submitAdvancedJob({
        starting_url: store.startingUrl,
        starting_title: store.startingTitle,
        site_url: store.siteUrl,
        site_title: store.siteTitle,
        site_description: store.siteDescription,
        links_to_footnotes: store.linksToFootnotes,
        add_toc: store.addTOC,
        max_posts: store.maxPosts,
        custom_search_opt: store.customSearchOpt,
        tag_name: store.tagName,
        attr_name: store.attrName,
        attr_value: store.attrValue,
        pre_string: store.preString,
        parent_tag: store.parentTag,
      }),
    onSuccess: ({ job_id }) => {
      store.setActiveJobId(job_id)
      navigate(`/working/${job_id}`)
    },
  })
}
