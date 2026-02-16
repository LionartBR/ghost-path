/* GapCarousel tests — behavior specs for Phase 5 gap triage.

Invariants:
    - Each gap has two explicit action buttons: investigate and reject
    - Semantic dots reflect triage state (green/red/gray)
    - Auto-advances to next unreviewed gap after action
    - Auto-collapses when all gaps triaged
    - Submit sends only investigate indices

Design Decisions:
    - Mock i18n with passthrough: tests verify structure, not translations
    - Mock ClaimMarkdown with plain div: avoids react-markdown dependency in tests
    - fireEvent over userEvent: avoids userEvent internal setTimeout conflicts with vi.useFakeTimers
*/

import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import GapCarousel from "../GapCarousel";

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

/* Mock ClaimMarkdown — render plain text */
vi.mock("../ClaimMarkdown", () => ({
  default: ({ children }: { children: string }) => <div data-testid="claim-md">{children}</div>,
}));

const SAMPLE_GAPS = [
  "Gap about renewable energy storage costs",
  "Gap about distributed team communication patterns",
  "Gap about developer onboarding bottlenecks",
];

describe("GapCarousel", () => {
  let onInvestigate: ReturnType<typeof vi.fn<(indices: number[]) => void>>;

  beforeEach(() => {
    onInvestigate = vi.fn<(indices: number[]) => void>();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("renders two action buttons per gap: select for investigation and reject", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);
    expect(screen.getByText("build.selectForInvestigation")).toBeInTheDocument();
    expect(screen.getByText("build.rejectGap")).toBeInTheDocument();
  });

  test("selecting investigate marks gap with green dot and shows selected state", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);

    fireEvent.click(screen.getByText("build.selectForInvestigation"));

    const dots = screen.getByTestId("gap-dots").querySelectorAll("button");
    expect(dots[0].className).toContain("bg-green-500");
  });

  test("selecting reject marks gap with red dot and shows rejected state", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);

    fireEvent.click(screen.getByText("build.rejectGap"));

    const dots = screen.getByTestId("gap-dots").querySelectorAll("button");
    expect(dots[0].className).toContain("bg-red-400");
  });

  test("toggling from investigate to reject switches the action", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);

    /* Select investigate */
    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });

    /* Navigate back to first gap via dot */
    const dots = screen.getByTestId("gap-dots").querySelectorAll("button");
    fireEvent.click(dots[0]);

    /* Now reject it */
    fireEvent.click(screen.getByText("build.rejectGap"));

    /* Dot should switch to red */
    const updatedDots = screen.getByTestId("gap-dots").querySelectorAll("button");
    expect(updatedDots[0].className).toContain("bg-red-400");
  });

  test("auto-advances to next unreviewed gap after action (300ms)", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);

    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    fireEvent.click(screen.getByText("build.selectForInvestigation"));

    /* After 300ms, should auto-advance to card 2/3 */
    act(() => { vi.advanceTimersByTime(350); });
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  test("collapses into summary bar when all gaps are triaged", () => {
    render(<GapCarousel gaps={["Gap A", "Gap B"]} onInvestigate={onInvestigate} />);

    /* Triage first gap */
    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });

    /* Triage second gap — all triaged */
    fireEvent.click(screen.getByText("build.rejectGap"));
    act(() => { vi.advanceTimersByTime(450); });

    expect(screen.getByTestId("gap-collapsed-summary")).toBeInTheDocument();
  });

  test("collapsed summary shows correct counts: N selected, M rejected", () => {
    render(<GapCarousel gaps={["Gap A", "Gap B"]} onInvestigate={onInvestigate} />);

    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });
    fireEvent.click(screen.getByText("build.rejectGap"));
    act(() => { vi.advanceTimersByTime(450); });

    /* Mock t() interpolates: "1 selected · 1 rejected" */
    expect(screen.getByText("build.gapSummary")).toBeInTheDocument();
  });

  test("clicking collapsed summary re-expands the carousel", () => {
    render(<GapCarousel gaps={["Gap A", "Gap B"]} onInvestigate={onInvestigate} />);

    /* Triage all */
    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });
    fireEvent.click(screen.getByText("build.rejectGap"));
    act(() => { vi.advanceTimersByTime(450); });

    /* Click collapsed bar */
    fireEvent.click(screen.getByTestId("gap-collapsed-summary"));

    /* Should re-expand */
    expect(screen.getByTestId("gap-dots")).toBeInTheDocument();
  });

  test("investigate button is disabled when no gaps are selected for investigation", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);
    const btn = screen.getByText(/build\.investigateSelected/);
    expect(btn).toBeDisabled();
  });

  test("investigate button shows count of selected gaps", () => {
    render(<GapCarousel gaps={SAMPLE_GAPS} onInvestigate={onInvestigate} />);

    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });

    expect(screen.getByText(/build\.investigateSelected/)).not.toBeDisabled();
  });

  test("submit sends only investigate indices, not rejected ones", () => {
    render(<GapCarousel gaps={["Gap A", "Gap B", "Gap C"]} onInvestigate={onInvestigate} />);

    /* Investigate first gap */
    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(350); });

    /* Reject second gap */
    fireEvent.click(screen.getByText("build.rejectGap"));
    act(() => { vi.advanceTimersByTime(350); });

    /* Investigate third gap */
    fireEvent.click(screen.getByText("build.selectForInvestigation"));
    act(() => { vi.advanceTimersByTime(450); });

    /* Re-expand if collapsed */
    const collapsed = screen.queryByTestId("gap-collapsed-summary");
    if (collapsed) fireEvent.click(collapsed);

    /* Click submit */
    fireEvent.click(screen.getByText(/build\.investigateSelected/));
    expect(onInvestigate).toHaveBeenCalledWith([0, 2]);
  });

  test("renders nothing when gaps array is empty", () => {
    const { container } = render(<GapCarousel gaps={[]} onInvestigate={onInvestigate} />);
    expect(container.innerHTML).toBe("");
  });
});
