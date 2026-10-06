import { redirect } from "next/navigation";
import { getUserSession } from "@/lib/auth";

export default async function HomePage() {
  const user = await getUserSession();

  if (user) {
    redirect("/liquidaciones");
  }

  redirect("/login");
}
