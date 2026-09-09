import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MethodologyView } from '../../src/ui/MethodologyView';

describe('MethodologyView', () => {
  it('marks the pipeline as designed, not as an executed/published result', () => {
    render(<MethodologyView />);

    const notice = screen.getByTestId('methodology-epistemic-notice');
    expect(notice).toHaveTextContent(/designed pipeline/i);
    expect(notice).toHaveTextContent(/not yet executed end-to-end/i);
    expect(notice).toHaveTextContent(/no stage below is currently backed by a published scientific result/i);

    // Must never claim the pipeline has already produced results.
    expect(screen.queryByText(/nexus has produced/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/verified results? (are|have been) published/i)).not.toBeInTheDocument();
  });

  it('links to ADR 0025 as the gate for showing real data on these stages', () => {
    render(<MethodologyView />);
    const link = screen.getByRole('link', { name: /adr 0025/i });
    expect(link).toHaveAttribute('href', expect.stringContaining('0025-scientific-results-publication-and-track-semantics.md'));
  });
});
