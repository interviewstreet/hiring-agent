import Link from "next/link";

/** The shared "nothing to show" panel: a message plus a link back to scoring. */
export function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty">
      <p>{message}</p>
      <Link className="empty-link" href="/">
        ← Score a resume
      </Link>
    </div>
  );
}
