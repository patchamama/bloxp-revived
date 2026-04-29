export interface BasicJobRequest {
  feed_url: string
  links_to_footnotes: boolean
  add_toc: boolean
}

export interface AdvancedJobRequest {
  starting_url: string
  starting_title: string
  site_url: string
  site_title: string
  site_description: string
  links_to_footnotes: boolean
  add_toc: boolean
  max_posts: number
  custom_search_opt: boolean
  tag_name: string
  attr_name: string
  attr_value: string
  pre_string: string
  parent_tag: boolean
}
