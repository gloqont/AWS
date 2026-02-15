import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const AUTH_BYPASS = process.env.NEXT_PUBLIC_AUTH_BYPASS?.trim().toLowerCase() === "true";

export default function Home() {
  if (AUTH_BYPASS) {
    redirect("/dashboard/portfolio-optimizer");
  }

  const token = cookies().get("gloqont_auth_token")?.value;
  if (token) {
    redirect("/dashboard/portfolio-optimizer");
  }
  redirect("/login");
}
