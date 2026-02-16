import { BrowserRouter, Routes, Route } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { SessionPage } from "./pages/SessionPage";
import { ReportPage } from "./pages/ReportPage";
import KnowledgeDocument from "./components/KnowledgeDocument";

const PREVIEW_MD = `# Knowledge Document: The Future of Distributed Systems

## 1. Problem Statement

How can we design distributed systems that maintain strong consistency guarantees while achieving horizontal scalability across geographic regions? This fundamental tension between consistency and availability (as formalized in the CAP theorem) remains one of the most challenging problems in modern software architecture.

## 2. Key Findings

### 2.1 Consensus Protocols Have Evolved Significantly

Modern consensus protocols like Raft and Multi-Paxos have made strong consistency more practical. Recent innovations in **leaderless replication** (e.g., EPaxos) reduce latency by eliminating the single-leader bottleneck.

### 2.2 CRDTs Offer an Alternative Path

Conflict-free Replicated Data Types provide eventual consistency with **mathematical guarantees** of convergence. They trade off some query expressiveness for the ability to operate without coordination.

> "CRDTs shift the complexity from the runtime protocol to the data type design itself." — Shapiro et al., 2011

### 2.3 Hybrid Approaches Are Most Promising

The most successful modern systems (Spanner, CockroachDB, YugabyteDB) use **hybrid approaches**:

- Strong consistency for critical paths (financial transactions)
- Eventual consistency for read-heavy, latency-sensitive operations
- Tunable consistency levels per-operation

## 3. Evidence Summary

| Source | Finding | Confidence |
|--------|---------|------------|
| Google Spanner (2012) | TrueTime enables global strong consistency | High |
| Amazon Aurora (2017) | Storage-level replication reduces coordination | High |
| Jepsen Testing | Many databases fail their consistency claims | Critical |

## 4. Contradictions Identified

1. **Latency vs. Consistency**: Stronger consistency requires more round-trips between nodes
2. **Scalability vs. Simplicity**: Horizontal scaling introduces operational complexity
3. **Cost vs. Availability**: Multi-region deployments are expensive but necessary for HA

## 5. Synthesis

The dialectical analysis reveals that the **false dichotomy** between consistency and availability can be resolved through:

1. Time-based ordering (TrueTime, hybrid logical clocks)
2. Workload-aware consistency tuning
3. Formal verification of protocol implementations

## 6. Practical Implications

- Start with strong consistency, weaken only where measured latency requires it
- Invest in observability: distributed tracing, consistency checking
- Use formal methods (TLA+) to verify critical protocol paths

## 7. Open Questions

- Can quantum computing fundamentally change consensus protocol design?
- How will edge computing affect consistency model choices?
- Will WebAssembly enable portable, verified consensus implementations?

## 8. Methodology Notes

This analysis employed the TRIZ dialectical method across 3 rounds of thesis-antithesis-synthesis, grounded in 12 web-sourced evidence items.

## 9. Confidence Assessment

Overall confidence: **Grounded** (0.82). Key claims supported by peer-reviewed research and production system evidence.

## 10. References

- Brewer, E. (2000). "Towards Robust Distributed Systems"
- Lamport, L. (1998). "The Part-Time Parliament"
- Shapiro, M. et al. (2011). "Conflict-free Replicated Data Types"
- Corbett, J. et al. (2012). "Spanner: Google's Globally-Distributed Database"
`;

function PreviewDocument() {
  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <KnowledgeDocument markdown={PREVIEW_MD} />
    </div>
  );
}

function Footer() {
  return (
    <footer className="w-full border-t border-gray-200/60 bg-white/60 backdrop-blur-sm py-5 px-6">
      <div className="max-w-7xl mx-auto flex flex-col items-center gap-1.5 text-xs text-gray-400">
        <span className="text-sm text-gray-600 font-medium">Built with Opus 4.6: A Claude Code Hackathon Project</span>
        <span>Developer: Arthur A. Martins</span>
        <a
          href="https://x.com/lionartmartins"
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-500 hover:text-blue-500 transition-colors mt-1"
        >
          @lionartmartins
        </a>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen">
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/session/:sessionId" element={<SessionPage />} />
            <Route path="/knowledge/:sessionId" element={<ReportPage />} />
            <Route path="/report/:sessionId" element={<ReportPage />} />
            <Route path="/preview/document" element={<PreviewDocument />} />
          </Routes>
        </div>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
