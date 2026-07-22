import { useLayoutEffect, useState, RefObject } from 'react'

// CSS Grid's items-stretch only stretches the wrapper div to the row's max-content
// height — it does not shrink a taller sibling's own content to fit. Matching two
// cards' visible bottoms exactly (one fixed-height, one variable-length list)
// needs a real measurement of the source element, kept in sync as it resizes.
export function useMatchHeight(sourceRef: RefObject<HTMLElement | null>): number | undefined {
  const [height, setHeight] = useState<number | undefined>(undefined)

  useLayoutEffect(() => {
    const el = sourceRef.current
    if (!el) return
    const update = () => setHeight(el.getBoundingClientRect().height)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [sourceRef])

  return height
}
