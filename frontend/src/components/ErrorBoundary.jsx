import { Component } from 'react'
import { AlertTriangle } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('FleetGuard AI render error:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
          <AlertTriangle size={26} className="text-risk-amber mb-3" />
          <p className="font-semibold text-ink mb-1">Something broke on this screen</p>
          <p className="text-sm text-ink-dim max-w-md mb-4">{this.state.error.message}</p>
          <button
            onClick={() => this.setState({ error: null })}
            className="px-4 py-2 rounded-lg bg-brand-soft text-brand-dim text-sm font-semibold hover:bg-brand/20 transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
