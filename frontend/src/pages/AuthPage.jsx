import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import { fetchMe, getToken, login, register, setSession } from "../lib/api";
import "../styles/auth.css";

const copyByMode = {
  signin: {
    title: "Welcome back",
    subtitle: "Sign in to continue your study session.",
    button: "Sign in",
    helperPrefix: "New here?",
    helperAction: "Create an account",
  },
  register: {
    title: "Create your account",
    subtitle: "Start studying smarter in minutes.",
    button: "Create account",
    helperPrefix: "Already have an account?",
    helperAction: "Sign in",
  },
};

export default function AuthPage() {
  const [mode, setMode] = useState("signin");
  const [signinData, setSigninData] = useState({ email: "", password: "" });
  const [registerData, setRegisterData] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const copy = copyByMode[mode];

  useEffect(() => {
    if (getToken()) {
      fetchMe()
        .then(() => navigate("/rooms", { replace: true }))
        .catch(() => {});
    }
  }, [navigate]);

  async function handleSigninSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await login(signinData);
      setSession(result.access_token, {
        user_id: result.user_id,
        name: result.name,
        email: signinData.email,
      });
      navigate("/rooms", { replace: true });
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRegisterSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      await register(registerData);
      const result = await login({
        email: registerData.email,
        password: registerData.password,
      });
      setSession(result.access_token, {
        user_id: result.user_id,
        name: result.name,
        email: registerData.email,
      });
      navigate("/rooms", { replace: true });
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-layout">
        <div className="hero-panel">
          <div className="hero-panel__glow hero-panel__glow--top" />
          <div className="hero-panel__glow hero-panel__glow--bottom" />

          <header className="brand-row">
            <BrandMark className="brand-mark" />
            <span className="brand-name">AI Study Partner</span>
          </header>

          <div className="hero-copy">
            <span className="hero-badge">Your AI study companion</span>
            <h1 className="hero-title">
              Turn dense PDFs into <span>clear summaries,</span> quizzes &amp; flashcards.
            </h1>
            <p className="hero-description">
              Create study rooms, upload your material, and learn faster with an AI partner that actually reads your documents.
            </p>
          </div>

          <footer className="hero-footer">&copy; 2026 AI Study Partner</footer>
        </div>

        <div className="form-panel">
          <section className="auth-card">
            <div className="auth-card__inner">
              <div className="auth-copy">
                <h2>{copy.title}</h2>
                <p>{copy.subtitle}</p>
              </div>

              {error ? <div className="auth-error">{error}</div> : null}

              <div className="auth-toggle" role="tablist" aria-label="Authentication mode">
                <button
                  className={`auth-toggle__button ${mode === "signin" ? "is-active" : ""}`}
                  type="button"
                  onClick={() => setMode("signin")}
                >
                  Sign in
                </button>
                <button
                  className={`auth-toggle__button ${mode === "register" ? "is-active" : ""}`}
                  type="button"
                  onClick={() => setMode("register")}
                >
                  Register
                </button>
              </div>

              {mode === "signin" ? (
                <form className="auth-form" onSubmit={handleSigninSubmit}>
                  <label className="field-group">
                    <span>Email</span>
                    <input
                      type="email"
                      placeholder="you@school.edu"
                      autoComplete="email"
                      value={signinData.email}
                      onChange={(event) => setSigninData((current) => ({ ...current, email: event.target.value }))}
                      required
                    />
                  </label>

                  <label className="field-group">
                    <span>Password</span>
                    <input
                      type="password"
                      placeholder="••••••••"
                      autoComplete="current-password"
                      value={signinData.password}
                      onChange={(event) => setSigninData((current) => ({ ...current, password: event.target.value }))}
                      required
                    />
                  </label>

                  <button className="auth-submit" type="submit" disabled={loading}>
                    {loading ? "Signing in..." : copy.button}
                  </button>

                  <p className="auth-footer-copy">
                    {copy.helperPrefix}{" "}
                    <button className="auth-inline-link" type="button" onClick={() => setMode("register")}>
                      {copy.helperAction}
                    </button>
                  </p>
                </form>
              ) : (
                <form className="auth-form" onSubmit={handleRegisterSubmit}>
                  <label className="field-group">
                    <span>Name</span>
                    <input
                      type="text"
                      placeholder="Ada Lovelace"
                      autoComplete="name"
                      value={registerData.name}
                      onChange={(event) => setRegisterData((current) => ({ ...current, name: event.target.value }))}
                      required
                    />
                  </label>

                  <label className="field-group">
                    <span>Email</span>
                    <input
                      type="email"
                      placeholder="you@school.edu"
                      autoComplete="email"
                      value={registerData.email}
                      onChange={(event) => setRegisterData((current) => ({ ...current, email: event.target.value }))}
                      required
                    />
                  </label>

                  <label className="field-group">
                    <span>Password</span>
                    <input
                      type="password"
                      placeholder="••••••••"
                      autoComplete="new-password"
                      value={registerData.password}
                      onChange={(event) => setRegisterData((current) => ({ ...current, password: event.target.value }))}
                      required
                    />
                  </label>

                  <button className="auth-submit" type="submit" disabled={loading}>
                    {loading ? "Creating account..." : copy.button}
                  </button>

                  <p className="auth-footer-copy">
                    {copy.helperPrefix}{" "}
                    <button className="auth-inline-link" type="button" onClick={() => setMode("signin")}>
                      {copy.helperAction}
                    </button>
                  </p>
                </form>
              )}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
