import type { ReactNode } from "react";
import type { OnboardingState } from "../api";
import { Logo } from "../components/Logo";

type OnboardingLayoutProps = {
  state: OnboardingState;
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function OnboardingLayout({ state, title, description, children, footer }: OnboardingLayoutProps) {
  const current = Math.max(
    0,
    state.steps.findIndex((step) => !step.done),
  );

  return (
    <div className="onboarding-screen">
      <header className="onboarding-top">
        <Logo className="auth-logo" />
        <div className="onboarding-progress" aria-hidden="true">
          {state.steps.map((step, index) => (
            <span
              key={step.key}
              className={index < current ? "is-done" : index === current ? "is-current" : undefined}
            />
          ))}
        </div>
        <span className="onboarding-count">
          {Math.min(current + 1, state.steps.length)}/{state.steps.length}
        </span>
      </header>

      <div className="onboarding-scroll">
        <header className="onboarding-head">
          <h1>{title}</h1>
          <p>{description}</p>
        </header>
        {children}
      </div>

      {footer ? <footer className="onboarding-footer">{footer}</footer> : null}
    </div>
  );
}
