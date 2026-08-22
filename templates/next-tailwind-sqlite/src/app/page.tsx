export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold tracking-tight">{{PROJECT_NAME}}</h1>
      <p className="text-zinc-400">
        Scaffolded by salarymen. The board drives what gets built next.
      </p>
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 px-6 py-4 text-sm text-zinc-300">
        Next.js 15 · Tailwind 4 · SQLite · TypeScript strict
      </div>
    </main>
  );
}
