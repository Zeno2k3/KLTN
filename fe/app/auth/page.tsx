import AuthBrandPanel from "./_components/AuthBrandPanel";
import AuthForm from "./_components/AuthForm";

export default function AuthPage() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", fontFamily: "var(--font-body)", color: "var(--text-body)" }}>
      <AuthBrandPanel />
      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 24px", background: "radial-gradient(600px 380px at 90% -10%, var(--brand-subtle) 0%, rgba(247,250,250,0) 60%)" }}>
        <AuthForm />
      </main>
    </div>
  );
}
