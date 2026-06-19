import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";

/**
 * Root page — redirects to dashboard if authenticated, else to login.
 */
export default async function HomePage() {
  const user = await getUserSession();

  if (user) {
    redirect("/inicio");
  } else {
    redirect("/login");
  }
}
