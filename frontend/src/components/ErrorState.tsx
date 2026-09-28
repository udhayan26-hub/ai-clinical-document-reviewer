import { Link } from "react-router-dom";
import { ApiError } from "../services/apiClient";

interface Props {
  error: unknown;
  onRetry?: () => void;
}

function describe(error: unknown): { title: string; message: string; requestId?: string | null; notFound?: boolean } {
  if (error instanceof ApiError) {
    if (error.isNetworkError) {
      return { title: "Can't reach the server", message: error.message };
    }
    if (error.code === "NOT_FOUND") {
      return {
        title: "Analysis not found",
        message: "This analysis may have been deleted or the link may be incorrect.",
        notFound: true,
      };
    }
    return { title: `Something went wrong (${error.code})`, message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    return { title: "Something went wrong", message: error.message };
  }
  return { title: "Something went wrong", message: "An unexpected error occurred." };
}

export default function ErrorState({ error, onRetry }: Props) {
  const { title, message, requestId, notFound } = describe(error);
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-6 py-14 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-6 w-6">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-rose-900">{title}</h3>
      <p className="max-w-md text-sm text-rose-700">{message}</p>
      {requestId && <p className="text-xs text-rose-400">Request ID: {requestId}</p>}
      {notFound ? (
        <Link
          to="/analyses"
          className="mt-1 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-rose-700 ring-1 ring-inset ring-rose-300 hover:bg-rose-50"
        >
          Back to History
        </Link>
      ) : (
        onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-1 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-rose-700 ring-1 ring-inset ring-rose-300 hover:bg-rose-50"
          >
            Try again
          </button>
        )
      )}
    </div>
  );
}
