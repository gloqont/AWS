"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  confirmResetPassword,
  confirmSignUp,
  fetchAuthSession,
  resendSignUpCode,
  resetPassword,
  signIn,
  signUp,
} from "aws-amplify/auth";
import { configureAmplify } from "@/lib/amplify-client";

type AuthMode = "signin" | "signup";
type SocialProvider = "Google" | "SignInWithApple" | "Facebook";

const NEXT_PATH = "/dashboard/portfolio-optimizer";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [verificationCode, setVerificationCode] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [forgotFlow, setForgotFlow] = useState<"none" | "request" | "confirm">("none");
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<SocialProvider | "">("");
  const [errorBanner, setErrorBanner] = useState("");
  const [notice, setNotice] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const callbackError = searchParams.get("error");

  const title = useMemo(() => {
    if (forgotFlow !== "none") return "Reset password";
    if (awaitingConfirmation) return "Confirm your account";
    return mode === "signin" ? "Sign in" : "Create account";
  }, [awaitingConfirmation, forgotFlow, mode]);

  function validateEmailPasswordForm() {
    const errors: Record<string, string> = {};

    if (!email.trim()) {
      errors.email = "Email is required.";
    } else if (!/^\S+@\S+\.\S+$/.test(email.trim())) {
      errors.email = "Enter a valid email address.";
    }

    if (!password) {
      errors.password = "Password is required.";
    } else if (password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }

    if (mode === "signup" && password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function persistSession(remember: boolean) {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString() || "";
    const accessToken = session.tokens?.accessToken?.toString() || "";

    if (!idToken || !accessToken) {
      throw new Error("Sign in succeeded, but Cognito session tokens were missing.");
    }

    const res = await fetch("/api/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        idToken,
        accessToken,
        refreshToken: session.tokens?.refreshToken?.toString(),
        rememberMe: remember,
      }),
    });

    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.error || "Failed to create session cookie.");
    }

    await fetch("/api/user/sync", { method: "POST" }).catch(() => null);
  }

  async function handleSignInSubmit(e: FormEvent) {
    e.preventDefault();
    setNotice("");
    setErrorBanner("");

    if (!validateEmailPasswordForm()) return;

    try {
      configureAmplify();
      setLoading(true);
      const response = await signIn({
        username: email.trim(),
        password,
      });

      if (response.nextStep.signInStep !== "DONE") {
        throw new Error("Additional sign-in steps are required. Please complete Cognito setup for this flow.");
      }

      await persistSession(rememberMe);
      router.push(NEXT_PATH);
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUpSubmit(e: FormEvent) {
    e.preventDefault();
    setNotice("");
    setErrorBanner("");

    if (!validateEmailPasswordForm()) return;

    try {
      configureAmplify();
      setLoading(true);
      await signUp({
        username: email.trim(),
        password,
        options: {
          userAttributes: {
            email: email.trim(),
          },
        },
      });

      setAwaitingConfirmation(true);
      setNotice("Verification code sent. Check your email.");
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to create account.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmSignUp(e: FormEvent) {
    e.preventDefault();
    setNotice("");
    setErrorBanner("");

    if (!verificationCode.trim()) {
      setFieldErrors({ verificationCode: "Verification code is required." });
      return;
    }

    try {
      configureAmplify();
      setLoading(true);
      await confirmSignUp({
        username: email.trim(),
        confirmationCode: verificationCode.trim(),
      });

      const response = await signIn({ username: email.trim(), password });
      if (response.nextStep.signInStep !== "DONE") {
        throw new Error("Account confirmed. Please sign in.");
      }

      await persistSession(rememberMe);
      router.push(NEXT_PATH);
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to confirm sign-up.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResendSignUpCode() {
    setNotice("");
    setErrorBanner("");
    try {
      configureAmplify();
      setLoading(true);
      await resendSignUpCode({ username: email.trim() });
      setNotice("A new verification code has been sent.");
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to resend code.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestReset(e: FormEvent) {
    e.preventDefault();
    setNotice("");
    setErrorBanner("");

    if (!email.trim()) {
      setFieldErrors({ email: "Email is required." });
      return;
    }

    try {
      configureAmplify();
      setLoading(true);
      await resetPassword({ username: email.trim() });
      setForgotFlow("confirm");
      setNotice("Password reset code sent to your email.");
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to start password reset.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmReset(e: FormEvent) {
    e.preventDefault();
    setNotice("");
    setErrorBanner("");

    const errors: Record<string, string> = {};
    if (!resetCode.trim()) errors.resetCode = "Reset code is required.";
    if (!newPassword || newPassword.length < 8) errors.newPassword = "New password must be at least 8 characters.";
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;

    try {
      configureAmplify();
      setLoading(true);
      await confirmResetPassword({
        username: email.trim(),
        confirmationCode: resetCode.trim(),
        newPassword,
      });
      setForgotFlow("none");
      setMode("signin");
      setNotice("Password updated. You can sign in now.");
    } catch (error: any) {
      setErrorBanner(error?.message || "Unable to reset password.");
    } finally {
      setLoading(false);
    }
  }

  async function startSocial(provider: SocialProvider) {
    setNotice("");
    setErrorBanner("");
    setSocialLoading(provider);

    try {
      const res = await fetch("/api/auth/hosted-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          provider,
          nextPath: NEXT_PATH,
          rememberMe,
        }),
      });

      const payload = await res.json();
      if (!res.ok || !payload.url) {
        throw new Error(payload.error || "Could not start social sign in.");
      }

      window.location.assign(payload.url);
    } catch (error: any) {
      setErrorBanner(error?.message || "Could not start social sign in.");
      setSocialLoading("");
    }
  }

  async function handleLogoutEverywhere() {
    const res = await fetch("/api/auth/logout", { method: "POST" });
    const payload = await res.json().catch(() => ({}));
    window.location.assign(payload.logoutUrl || "/login");
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#070b14] text-slate-100">
      <div className="app-bubbles pointer-events-none absolute inset-0 z-0" aria-hidden="true" />

      <div className="relative z-10 flex min-h-screen items-center justify-center p-5 sm:p-8">
        <section className="w-full max-w-[460px] rounded-3xl border border-slate-800/90 bg-[#0b1222]/90 p-6 shadow-[0_24px_60px_rgba(2,6,23,0.62)] backdrop-blur md:p-8">
          <header className="mb-6 text-center">
            <img src="/gloqont-logo.svg" alt="GLOQONT" className="mx-auto h-14 w-14 rounded-2xl ring-1 ring-slate-700/70" />
            <div className="mt-3 text-xs uppercase tracking-[0.2em] text-indigo-300">GLOQONT</div>
            <h1 className="mt-3 text-2xl font-semibold text-white">{title}</h1>
          </header>

          {callbackError ? (
            <div className="mb-4 rounded-lg border border-red-500/40 bg-red-950/35 px-3 py-2 text-sm text-red-200" role="alert">
              {callbackError}
            </div>
          ) : null}

          {errorBanner ? (
            <div className="mb-4 rounded-lg border border-red-500/40 bg-red-950/35 px-3 py-2 text-sm text-red-200" role="alert">
              {errorBanner}
            </div>
          ) : null}

          {notice ? (
            <div className="mb-4 rounded-lg border border-emerald-500/40 bg-emerald-950/35 px-3 py-2 text-sm text-emerald-200" role="status">
              {notice}
            </div>
          ) : null}

          {forgotFlow === "none" && !awaitingConfirmation ? (
            <div className="mb-4 grid grid-cols-2 rounded-xl border border-slate-800 bg-slate-950/45 p-1">
              <button
                type="button"
                onClick={() => setMode("signin")}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${mode === "signin" ? "bg-indigo-500 text-white" : "text-slate-300"}`}
                aria-pressed={mode === "signin"}
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={() => setMode("signup")}
                className={`rounded-lg px-3 py-2 text-sm font-medium ${mode === "signup" ? "bg-indigo-500 text-white" : "text-slate-300"}`}
                aria-pressed={mode === "signup"}
              >
                Create account
              </button>
            </div>
          ) : null}

          {forgotFlow === "none" && !awaitingConfirmation ? (
            <>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => startSocial("Google")}
                  disabled={Boolean(socialLoading) || loading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  aria-label="Continue with Google"
                >
                  <img src="/icons/google.svg" alt="" className="h-4 w-4" aria-hidden="true" />
                  {socialLoading === "Google" ? "Redirecting..." : "Continue with Google"}
                </button>
                <button
                  type="button"
                  onClick={() => startSocial("SignInWithApple")}
                  disabled={Boolean(socialLoading) || loading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  aria-label="Continue with Apple"
                >
                  <img src="/icons/apple.svg" alt="" className="h-4 w-4" aria-hidden="true" />
                  {socialLoading === "SignInWithApple" ? "Redirecting..." : "Continue with Apple"}
                </button>
                <button
                  type="button"
                  onClick={() => startSocial("Facebook")}
                  disabled={Boolean(socialLoading) || loading}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-100 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  aria-label="Continue with Facebook"
                >
                  <img src="/icons/facebook.svg" alt="" className="h-4 w-4" aria-hidden="true" />
                  {socialLoading === "Facebook" ? "Redirecting..." : "Continue with Facebook"}
                </button>
              </div>

              <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-[0.16em] text-slate-500">
                <div className="h-px flex-1 bg-slate-800" />
                or
                <div className="h-px flex-1 bg-slate-800" />
              </div>
            </>
          ) : null}

          {awaitingConfirmation ? (
            <form className="space-y-4" onSubmit={handleConfirmSignUp}>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">Verification code</span>
                <input
                  type="text"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-indigo-400 focus:ring"
                  autoComplete="one-time-code"
                  aria-invalid={Boolean(fieldErrors.verificationCode)}
                />
                {fieldErrors.verificationCode ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.verificationCode}</span> : null}
              </label>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Confirming..." : "Confirm account"}
              </button>

              <div className="flex gap-3 text-sm">
                <button
                  type="button"
                  onClick={handleResendSignUpCode}
                  disabled={loading}
                  className="text-indigo-300 underline-offset-4 hover:underline disabled:opacity-60"
                >
                  Resend code
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAwaitingConfirmation(false);
                    setMode("signin");
                    setVerificationCode("");
                  }}
                  className="text-slate-300 underline-offset-4 hover:underline"
                >
                  Back to sign in
                </button>
              </div>
            </form>
          ) : forgotFlow === "request" ? (
            <form className="space-y-4" onSubmit={handleRequestReset}>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-indigo-400 focus:ring"
                  autoComplete="email"
                  aria-invalid={Boolean(fieldErrors.email)}
                />
                {fieldErrors.email ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.email}</span> : null}
              </label>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Sending..." : "Send reset code"}
              </button>

              <button
                type="button"
                onClick={() => setForgotFlow("none")}
                className="text-sm text-slate-300 underline-offset-4 hover:underline"
              >
                Back to sign in
              </button>
            </form>
          ) : forgotFlow === "confirm" ? (
            <form className="space-y-4" onSubmit={handleConfirmReset}>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">Reset code</span>
                <input
                  type="text"
                  value={resetCode}
                  onChange={(e) => setResetCode(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-indigo-400 focus:ring"
                  autoComplete="one-time-code"
                  aria-invalid={Boolean(fieldErrors.resetCode)}
                />
                {fieldErrors.resetCode ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.resetCode}</span> : null}
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">New password</span>
                <div className="relative">
                  <input
                    type={showNewPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 pr-16 text-slate-100 outline-none ring-indigo-400 focus:ring"
                    autoComplete="new-password"
                    aria-invalid={Boolean(fieldErrors.newPassword)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                  >
                    {showNewPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {fieldErrors.newPassword ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.newPassword}</span> : null}
              </label>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Updating..." : "Update password"}
              </button>

              <button
                type="button"
                onClick={() => setForgotFlow("none")}
                className="text-sm text-slate-300 underline-offset-4 hover:underline"
              >
                Back to sign in
              </button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={mode === "signin" ? handleSignInSubmit : handleSignUpSubmit}>
              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none ring-indigo-400 focus:ring"
                  autoComplete="email"
                  aria-invalid={Boolean(fieldErrors.email)}
                  required
                />
                {fieldErrors.email ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.email}</span> : null}
              </label>

              <label className="block text-sm">
                <span className="mb-1 block text-slate-300">Password</span>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 pr-16 text-slate-100 outline-none ring-indigo-400 focus:ring"
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    aria-invalid={Boolean(fieldErrors.password)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                {fieldErrors.password ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.password}</span> : null}
              </label>

              {mode === "signup" ? (
                <label className="block text-sm">
                  <span className="mb-1 block text-slate-300">Confirm password</span>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 pr-16 text-slate-100 outline-none ring-indigo-400 focus:ring"
                      autoComplete="new-password"
                      aria-invalid={Boolean(fieldErrors.confirmPassword)}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((v) => !v)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
                    >
                      {showConfirmPassword ? "Hide" : "Show"}
                    </button>
                  </div>
                  {fieldErrors.confirmPassword ? <span className="mt-1 block text-xs text-red-300">{fieldErrors.confirmPassword}</span> : null}
                </label>
              ) : null}

              {mode === "signin" ? (
                <div className="flex items-center justify-between text-sm">
                  <label className="inline-flex items-center gap-2 text-slate-300">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-indigo-500"
                    />
                    Remember me
                  </label>

                  <button
                    type="button"
                    onClick={() => setForgotFlow("request")}
                    className="text-indigo-300 underline-offset-4 hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loading || Boolean(socialLoading)}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true" />
                    Processing...
                  </>
                ) : mode === "signin" ? (
                  "Sign in"
                ) : (
                  "Create account"
                )}
              </button>

              <div className="text-center text-sm text-slate-300">
                {mode === "signin" ? "Don't have an account? " : "Already have an account? "}
                <button
                  type="button"
                  onClick={() => {
                    setMode(mode === "signin" ? "signup" : "signin");
                    setFieldErrors({});
                    setErrorBanner("");
                  }}
                  className="text-indigo-300 underline-offset-4 hover:underline"
                >
                  {mode === "signin" ? "Sign up" : "Sign in"}
                </button>
              </div>
            </form>
          )}

          <p className="mt-6 text-center text-xs leading-relaxed text-slate-400">
            By continuing, you agree to our Terms and Privacy Policy.
          </p>

          <button
            type="button"
            onClick={handleLogoutEverywhere}
            className="mt-3 w-full text-xs text-slate-500 underline-offset-4 hover:underline"
          >
            Clear local session and sign out everywhere
          </button>
        </section>
      </div>
    </main>
  );
}
