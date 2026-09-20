const STEPS = [
  { number: 1, title: 'Request', label: 'Procurement Details' },
  { number: 2, title: 'Eligibility', label: 'Centre Verification' },
  { number: 3, title: 'Recommendation', label: 'Optimal Centre' },
  { number: 4, title: 'Slot', label: 'Time Window' },
  { number: 5, title: 'Confirmation', label: 'Arrival Token' },
];

export default function StepIndicator({ currentStep }) {
  return (
    <nav className="step-indicator-wrapper" aria-label="Progress Stepper">
      <div className="step-indicator">
        {STEPS.map((step) => {
          const isCompleted = currentStep > step.number;
          const isCurrent = currentStep === step.number;

          let stepClass = 'step-item';
          if (isCompleted) stepClass += ' step-completed';
          if (isCurrent) stepClass += ' step-active';

          return (
            <div key={step.number} className={stepClass}>
              <div className="step-circle" aria-current={isCurrent ? 'step' : undefined}>
                {isCompleted ? '✓' : step.number}
              </div>
              <div className="step-labels">
                <span className="step-title">{step.title}</span>
                <span className="step-desc">{step.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </nav>
  );
}
