import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";
import { ProtectedSidebar } from "@/components-app/sidebar/ProtectedSidebar";

/**
 * Protected layout - wraps all authenticated routes with sidebar.
 * Server Component: checks auth server-side before rendering.
 */
export default async function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getUserSession();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="flex h-svh w-full overflow-hidden">
      {/* Sidebar — collapses to 0 width on mobile; sidebar component handles its own mobile overlay */}
      <div className="shrink-0">
        <ProtectedSidebar user={user} />
      </div>

      {/* Main content area - takes remaining space */}
      <main className="flex-1 min-w-0 overflow-auto bg-background">
        {children}
      </main>
    </div>
  );
}
