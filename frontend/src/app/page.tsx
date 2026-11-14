import { redirect } from "next/navigation";

/** Până există ecranul „Cine ești?”, pornirea duce la catalogul de componente. Apoi: redirect("/login"). */
export default function Home(): never {
  redirect("/kit");
}
