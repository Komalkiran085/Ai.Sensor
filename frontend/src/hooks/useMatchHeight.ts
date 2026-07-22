import { useCallback, useLayoutEffect, useState } from 'react'

// CSS Grid's items-stretch only stretches the wrapper div to the row's max-content
// height — it does not shrink a taller sibling's own content to fit. Matching two
// cards' visible bottoms exactly (one fixed-height, one variable-length list)
// needs a real measurement of the source element, kept in sync as it resizes.
//
// A plain useRef won't do here: its identity never changes, so an effect keyed on
// `[sourceRef]` only ever runs once — if the ref'd element unmounts and remounts
// later (e.g. switching dashboard tabs and back), the ResizeObserver is left
// watching the original, now-detached node forever, and the returned height freezes
// at a stale value. A callback ref re-fires on every attach/detach, so it correctly
// re-observes the new element each time.
export function useMatchHeight(): [(el: HTMLElement | null) => void, number | undefined] {
  const [node, setNode] = useState<HTMLElement | null>(null)
  const [height, setHeight] = useState<number | undefined>(undefined)

  const ref = useCallback((el: HTMLElement | null) => setNode(el), [])

  useLayoutEffect(() => {
    if (!node) return
    const update = () => setHeight(node.getBoundingClientRect().height)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(node)
    return () => ro.disconnect()
  }, [node])

  return [ref, height]
}
