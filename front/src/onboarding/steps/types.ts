import type { OnboardingState } from "../../api";

export type StepProps = {
  state: OnboardingState;
  onDone: () => void;
};

export type SimpleStepProps = {
  onDone: () => void;
};
