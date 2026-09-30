import { BrandHeader } from "../shared/BrandHeader";
import { MatchesView } from "./MatchesView";

export function MatchesPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <BrandHeader />
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <MatchesView />
      </main>
    </div>
  );
}
