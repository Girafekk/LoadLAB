import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginFormGate } from "@/components/auth/auth-form-gate";
import { authContent } from "@/content/auth";

export const metadata: Metadata = {
  title: authContent.login.title,
  description: authContent.login.description,
};

export default function LoginPage() {
  // Suspense нужен, потому что форма читает параметр ?next= из адреса.
  return (
    <Suspense>
      <LoginFormGate />
    </Suspense>
  );
}
