import type { Metadata } from "next";

import { ProfileCard } from "@/components/auth/profile-card";
import { authContent } from "@/content/auth";

export const metadata: Metadata = {
  title: authContent.profile.title,
  description: authContent.profile.description,
};

export default function ProfilePage() {
  return <ProfileCard />;
}
