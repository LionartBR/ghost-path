/* BuildDecision tests — behavior specs for Phase 5 negative knowledge card.

Invariants:
    - Negative knowledge card rendered only when items exist
    - Card collapsed by default, expandable on click
    - Shows claim text, rejection reason, and round badge per rejected claim

Design Decisions:
    - Tests focus on negative knowledge card (new feature) — GapCarousel has own test file
    - Mock KnowledgeGraph + GapCarousel: isolate BuildDecision layout orchestration
*/

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi } from "vitest";
import BuildDecision from "../BuildDecision";
import type { BuildReviewData, UserInput } from "../../types";

/* Mock i18n — passthrough key + interpolation */
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts) {
        let result = key;
        for (const [k, v] of Object.entries(opts)) {
          result = result.replace(`{{${k}}}`, String(v));
        }
        return result;
      }
      return key;
    },
    i18n: { language: "en" },
  }),
}));

/* Mock heavy child components */
vi.mock("../KnowledgeGraph", () => ({
  default: () => <div data-testid="knowledge-graph" />,
}));
vi.mock("../GapCarousel", () => ({
  default: ({ gaps, onInvestigate }: { gaps: string[]; onInvestigate: (i: number[]) => void }) => (
    <div data-testid="gap-carousel" onClick={() => onInvestigate([0])}>{gaps.length} gaps</div>
  ),
}));
vi.mock("../ClaimMarkdown", () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

const BASE_DATA: BuildReviewData = {
  graph: { nodes: [], edges: [] },
  gaps: ["Gap 1"],
  negative_knowledge: [],
  round: 1,
  max_rounds_reached: false,
};

const NEG_KNOWLEDGE_DATA: BuildReviewData = {
  ...BASE_DATA,
  negative_knowledge: [
    { claim_text: "Rejected claim about solar efficiency", rejection_reason: "Insufficient evidence from 2024 data", round: 1 },
    { claim_text: "Rejected claim about battery costs", rejection_reason: "Contradicted by newer research", round: 2 },
  ],
};

describe("BuildDecision — Negative Knowledge", () => {
  const onSubmit = vi.fn<(input: UserInput) => void>();

  test("renders negative knowledge card when negative_knowledge has items", () => {
    render(<BuildDecision data={NEG_KNOWLEDGE_DATA} onSubmit={onSubmit} />);
    expect(screen.getByText("build.negativeKnowledge")).toBeInTheDocument();
  });

  test("negative knowledge card is collapsed by default", () => {
    render(<BuildDecision data={NEG_KNOWLEDGE_DATA} onSubmit={onSubmit} />);
    /* Toggle button visible, but list is not */
    expect(screen.getByTestId("neg-knowledge-toggle")).toBeInTheDocument();
    expect(screen.queryByTestId("neg-knowledge-list")).not.toBeInTheDocument();
  });

  test("negative knowledge card expands on click and shows claim text + rejection reason", async () => {
    const user = userEvent.setup();
    render(<BuildDecision data={NEG_KNOWLEDGE_DATA} onSubmit={onSubmit} />);

    await user.click(screen.getByTestId("neg-knowledge-toggle"));

    expect(screen.getByTestId("neg-knowledge-list")).toBeInTheDocument();
    expect(screen.getByText("Rejected claim about solar efficiency")).toBeInTheDocument();
    expect(screen.getByText("Insufficient evidence from 2024 data")).toBeInTheDocument();
    expect(screen.getByText("Rejected claim about battery costs")).toBeInTheDocument();
    expect(screen.getByText("Contradicted by newer research")).toBeInTheDocument();
    /* Round badges — two items, two badges */
    expect(screen.getAllByText("build.negKnowledgeRound")).toHaveLength(2);
  });

  test("hides negative knowledge card when negative_knowledge is empty", () => {
    render(<BuildDecision data={BASE_DATA} onSubmit={onSubmit} />);
    expect(screen.queryByText("build.negativeKnowledge")).not.toBeInTheDocument();
  });
});
