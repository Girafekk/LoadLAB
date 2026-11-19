import type { Metadata } from "next";

import { CourseManager } from "@/components/admin/course-manager";
import { adminContent } from "@/content/admin";

export const metadata: Metadata = {
  title: adminContent.courseTitle,
};

export default function AdminDashboardPage() {
  return <CourseManager />;
}
