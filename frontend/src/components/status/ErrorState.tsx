interface Props {
  message: string
  onRetry: () => void
  retryDisabled: boolean
}

export function ErrorState({ message, onRetry, retryDisabled }: Props) {
  return (
    <div className="status status--error" role="alert">
      <p>{message}</p>
      <button type="button" onClick={onRetry} disabled={retryDisabled}>
        다시 시도
      </button>
    </div>
  )
}
