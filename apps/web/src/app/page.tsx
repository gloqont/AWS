import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default function Home() {
  const token = cookies().get("gloqont_auth_token")?.value;
  if (token) {
    redirect("/dashboard/portfolio-optimizer");
  }
  redirect("/login");
}
