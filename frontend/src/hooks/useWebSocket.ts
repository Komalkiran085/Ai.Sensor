import { useEffect, useRef, useCallback, useState } from 'react'

type WSMessage = {
  type: string
  data: any
  timestamp: string
}

export function useWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const listenersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map())

  const subscribe = useCallback((type: string, callback: (data: any) => void) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set())
    }
    listenersRef.current.get(type)!.add(callback)
    return () => { listenersRef.current.get(type)?.delete(callback) }
  }, [])

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>

    function connect() {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        reconnectTimer = setTimeout(connect, 2000)
      }
      ws.onmessage = (ev) => {
        try {
          const msg: WSMessage = JSON.parse(ev.data)
          listenersRef.current.get(msg.type)?.forEach(cb => cb(msg.data))
        } catch {}
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      wsRef.current?.close()
    }
  }, [url])

  return { connected, subscribe }
}
