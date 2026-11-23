import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata = {
  title: "Страница не найдена",
};

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-2xl flex-col items-start justify-center px-4 py-16">
      <p className="text-sm font-medium text-muted-foreground">404</p>
      <h1 className="mt-2 text-3xl font-semibold text-balance">Страница не найдена</h1>
      <p className="mt-3 text-base leading-relaxed text-muted-foreground">
        Возможно, ссылка устарела или в адресе опечатка. Вернитесь на главную или
        откройте программу курса.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <Link href="/" className={cn(buttonVariants({ size: "lg" }), "px-4")}>
          На главную
        </Link>
        <Link
          href="/learn"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "px-4")}
        >
          К программе курса
        </Link>
      </div>
    </div>
  );
}
