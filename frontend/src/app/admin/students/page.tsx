import type { Metadata } from "next";

import { StudentsTable } from "@/components/admin/students-table";
import { adminContent } from "@/content/admin";

export const metadata: Metadata = {
  title: adminContent.students,
};

export default function AdminStudentsPage() {
  return <StudentsTable />;
}
