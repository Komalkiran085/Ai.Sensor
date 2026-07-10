import { X, FileText, Loader2 } from 'lucide-react'

type Props = {
  zone: string
  report: string
  loading: boolean
  onClose: () => void
}

export default function ReportModal({ zone, report, loading, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-8" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-bold text-white">Incident Report — {zone.replace(/_/g, ' ')}</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[65vh]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
              <span className="ml-3 text-gray-400">AI generating incident report...</span>
            </div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap text-gray-300 leading-relaxed">
              {report}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
