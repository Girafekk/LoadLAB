import type { Metadata } from "next";
import { Suspense } from "react";

import { RegisterForm } from "@/components/auth/register-form";
import { authContent } from "@/content/auth";

export const metadata: Metadata = {
  title: authContent.register.title,
  description: authContent.register.description,
};

export default function RegisterPage() {
  // Suspense нужен, потому что форма читает параметр ?next= из адреса.
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
