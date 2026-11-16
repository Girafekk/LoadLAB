import { About } from "@/components/home/about";
import { Advantages } from "@/components/home/advantages";
import { CourseCard } from "@/components/home/course-card";
import { Hero } from "@/components/home/hero";
import { UpcomingFeatures } from "@/components/home/upcoming-features";

export default function HomePage() {
  return (
    <>
      <Hero />
      <About />
      <CourseCard />
      <Advantages />
      <UpcomingFeatures />
    </>
  );
}
