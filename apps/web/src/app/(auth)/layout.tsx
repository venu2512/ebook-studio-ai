import { Logo } from "@/components/app/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-12 lg:px-12">
        <div className="mx-auto w-full max-w-sm">
          <div className="mb-8">
            <Logo />
          </div>
          {children}
        </div>
      </div>
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-primary via-violet-600 to-fuchsia-600 lg:block">
        <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_1px_1px,white_1px,transparent_0)] [background-size:24px_24px]" />
        <div className="relative flex h-full flex-col justify-between p-12 text-primary-foreground">
          <p className="text-sm font-medium uppercase tracking-widest opacity-80">
            eBook Studio AI
          </p>
          <blockquote className="max-w-md">
            <p className="font-serif text-3xl font-semibold leading-snug">
              “I described my topic over coffee. By lunch I had a chaptered, fact-checked,
              export-ready book.”
            </p>
            <footer className="mt-4 text-sm opacity-80">— An early-access author</footer>
          </blockquote>
          <div className="flex gap-6 text-sm opacity-90">
            <span>8 AI specialists</span>
            <span>PDF · EPUB · DOCX</span>
            <span>Cover & marketing kit</span>
          </div>
        </div>
      </div>
    </div>
  );
}
